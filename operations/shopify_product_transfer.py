import logging
import time
from connectors.shopify_api import ShopifyAPI

def transfer_products_manual(source_api: ShopifyAPI, dest_api: ShopifyAPI, product_ids: list, status='DRAFT', progress_callback=None):
    """
    Transfer selected products from source store to destination store manually.
    """
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    total = len(product_ids)

    for idx, product_id in enumerate(product_ids):
        if progress_callback:
            progress_callback(f"İşleniyor ({idx+1}/{total}): {product_id}")

        try:
            # 1. Fetch full details from Source
            source_product = source_api.get_product_full_details(product_id)
            if not source_product:
                results['failed'].append({'id': product_id, 'reason': 'Kaynak ürün bulunamadı'})
                continue

            title = source_product.get('title')

            # 2. Check if product exists in Destination (by handle or title)
            handle = source_product.get('handle')
            existing_products = dest_api.search_products(f"handle:{handle}")
            if not existing_products:
                 existing_products = dest_api.search_products(f"title:{title}")

            # If we want to allow updates, we can implement it here.
            # For now, let's assume we are creating new ones or skipping if exists.
            # But the requirement says "eksiksiz gönderebileceğim", implies creation.
            # If it exists, we might want to skip or update. Let's skip for safety or create with a suffix?
            # Usually manual sync implies "I want this product there".
            # Let's check if user wants to update? The prompt implies "send as draft", usually means new.

            if existing_products:
                # results['skipped'].append({'id': product_id, 'title': title, 'reason': 'Ürün zaten mevcut'})
                # continue
                # Update: User might want to overwrite or update. But let's stick to creation for now.
                # If we create with same handle, Shopify handles it by appending -1.
                pass

            # 3. Prepare Product Input for Destination
            product_input = {
                "title": title,
                "descriptionHtml": source_product.get('descriptionHtml'),
                "vendor": source_product.get('vendor'),
                "productType": source_product.get('productType'),
                "tags": source_product.get('tags'),
                "status": status,
                "handle": handle
            }

            # Options
            options = []
            source_options = source_product.get('options', [])
            # Filter out Title if it's "Default Title" (single variant product)
            if len(source_options) == 1 and source_options[0]['name'] == 'Title' and 'Default Title' in source_options[0]['values']:
                pass
            else:
                for opt in source_options:
                     options.append({"name": opt['name'], "values": [{"name": v} for v in opt['values']]})

            if options:
                product_input["productOptions"] = options

            # Images
            # We need to send image URLs. Shopify will download them.
            images_input = []
            for edge in source_product.get('images', {}).get('edges', []):
                node = edge['node']
                img = {"src": node['originalSrc']}
                if node.get('altText'):
                    img["altText"] = node['altText']
                images_input.append(img)

            # Note: We cannot attach images in productCreate easily if they are many.
            # But `productCreate` accepts `media` input which can take URLs.
            # Actually, `productCreate` input has `media` field as `[CreateMediaInput!]`.

            # 4. Create Product
            # We will use the mutation directly here or use a helper if available.
            # ShopifyAPI doesn't have a generic create_product that takes full input.

            mutation = """
            mutation productCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
                productCreate(input: $input, media: $media) {
                    product {
                        id
                        options {
                            id
                            name
                            position
                        }
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    title
                                    selectedOptions {
                                        name
                                        value
                                    }
                                }
                            }
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            # Prepare media input
            media_input = []
            for img in images_input:
                media_input.append({
                    "originalSource": img['src'],
                    "mediaContentType": "IMAGE",
                    "alt": img.get('altText')
                })

            vars = {"input": product_input}
            if media_input:
                vars["media"] = media_input

            create_result = dest_api.execute_graphql(mutation, vars)

            if errors := create_result.get('productCreate', {}).get('userErrors', []):
                results['failed'].append({'id': product_id, 'title': title, 'reason': f"Oluşturma hatası: {errors}"})
                continue

            new_product = create_result.get('productCreate', {}).get('product')
            new_product_id = new_product['id']

            # 5. Handle Variants (Price, SKU, Barcode, Inventory)
            # We need to map new variants to source variants based on Options.

            new_variants_map = {} # key: tuple of sorted option values, value: variant_id

            # If product has no options (Default Title), it has one variant
            if not options:
                # Single variant
                v_node = new_product['variants']['edges'][0]['node']
                new_variants_map[('Default Title',)] = v_node['id']
            else:
                for edge in new_product['variants']['edges']:
                    node = edge['node']
                    # Create a key from selected options
                    key = tuple(sorted([opt['value'] for opt in node['selectedOptions']]))
                    new_variants_map[key] = node['id']

            # Iterate source variants and update dest variants
            variants_update_inputs = []
            inventory_adjustments = []

            dest_location_id = dest_api.get_default_location_id()

            for edge in source_product.get('variants', {}).get('edges', []):
                src_v = edge['node']

                # Determine key for mapping
                if not options:
                     key = ('Default Title',)
                else:
                     key = tuple(sorted([opt['value'] for opt in src_v['selectedOptions']]))

                dest_v_id = new_variants_map.get(key)
                if dest_v_id:
                    # Update variant details
                    v_input = {
                        "id": dest_v_id,
                        "price": src_v.get('price'),
                        "compareAtPrice": src_v.get('compareAtPrice'),
                        "sku": src_v.get('sku'),
                        "barcode": src_v.get('barcode'),
                        "weight": src_v.get('weight'),
                        "weightUnit": src_v.get('weightUnit'),
                        "inventoryItem": {
                            "tracked": True # Enforce tracking
                            # "cost": src_v.get('inventoryItem', {}).get('unitCost', {}).get('amount') # Need to fetch cost if needed
                        }
                    }
                    variants_update_inputs.append(v_input)

                    # Prepare inventory adjustment
                    qty = src_v.get('inventoryQuantity', 0)
                    if qty > 0:
                        inventory_adjustments.append({
                            "inventoryItemId": dest_v_id, # Wait, we need inventoryItemId, not variantId.
                            # We can get inventoryItemId from variant update response OR fetch it again.
                            # But wait, productCreate response doesn't give inventoryItemId.
                            # We need to fetch it or rely on a second query.
                            # Actually, `productCreate` returns Variants. Let's check my query above.
                            # It returns `id` of variant. I didn't ask for `inventoryItem { id }`.
                            # I should update the query above.
                             "qty": qty
                        })

            # Update variants
            if variants_update_inputs:
                bulk_update_mutation = """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                    productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants {
                            id
                            inventoryItem {
                                id
                            }
                        }
                        userErrors {
                            field
                            message
                        }
                    }
                }
                """
                update_res = dest_api.execute_graphql(bulk_update_mutation, {
                    "productId": new_product_id,
                    "variants": variants_update_inputs
                })

                updated_variants = update_res.get('productVariantsBulkUpdate', {}).get('productVariants', [])

                # Now we have inventoryItemIds
                # Map variantId -> inventoryItemId
                var_inv_map = {v['id']: v['inventoryItem']['id'] for v in updated_variants}

                # Prepare real inventory adjustments
                final_inv_adjustments = []
                for adj in inventory_adjustments:
                    inv_id = var_inv_map.get(adj['inventoryItemId']) # This was holding variantId temporarily
                    if inv_id:
                        final_inv_adjustments.append({
                            "inventoryItemId": inv_id,
                            "availableQuantity": adj['qty']
                        })

                # Bulk Adjust Inventory
                if final_inv_adjustments:
                     # Reuse the logic from stock_sync or reimplement simple one here.
                     # Since we are in a different file, let's reimplement simple bulk set.
                     _set_inventory_quantities(dest_api, dest_location_id, final_inv_adjustments)

            results['success'].append({'id': product_id, 'title': title, 'new_id': new_product_id})

        except Exception as e:
            results['failed'].append({'id': product_id, 'reason': str(e)})
            logging.error(f"Transfer error for {product_id}: {e}")

    return results

def _set_inventory_quantities(api: ShopifyAPI, location_id, adjustments):
    mutation = """
    mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
        inventorySetQuantities(input: $input) {
            userErrors {
                field
                message
            }
        }
    }
    """

    # Chunking
    chunk_size = 50
    for i in range(0, len(adjustments), chunk_size):
        chunk = adjustments[i:i + chunk_size]
        quantities = [{
            "inventoryItemId": adj["inventoryItemId"],
            "locationId": location_id,
            "quantity": adj["availableQuantity"]
        } for adj in chunk]

        variables = {
            "input": {
                "reason": "correction",
                "name": "available",
                "ignoreCompareQuantity": True,
                "quantities": quantities
            }
        }
        api.execute_graphql(mutation, variables)

def sync_stock_only_shopify_to_shopify(source_api: ShopifyAPI, dest_api: ShopifyAPI, progress_callback=None):
    """
    Sync stock from Source to Destination based on SKU matching.
    Only updates stock. Does not create products.
    """
    if progress_callback:
        progress_callback("Kaynak mağaza stok verileri çekiliyor...")

    # 1. Fetch Source Stocks (SKU -> Qty)
    # Using `get_all_products_prices` method which returns sku, price, etc.
    # But it returns list of dicts. We need a map.
    source_products = source_api.get_all_products_prices(progress_callback=lambda msg: progress_callback(f"Kaynak: {msg}"))

    # We need quantity. `get_all_products_prices` (checking implementation) fetches:
    # node { id, variants { edges { node { id, sku, price, compareAtPrice } } } }
    # It DOES NOT fetch inventoryQuantity!
    # I need to either modify `get_all_products_prices` or create a new method `get_all_inventory_levels`.

    # Let's check `get_all_products_for_export`. It fetches `inventoryQuantity`.
    # "variants ... inventoryQuantity"
    # Yes. Let's use `get_all_products_for_export` or implement a lighter one.

    # Creating a lighter fetcher here for efficiency.
    source_skus = _fetch_all_skus_with_inventory(source_api, "Kaynak")

    if progress_callback:
        progress_callback(f"Kaynak mağazada {len(source_skus)} varyant bulundu. Hedef mağaza taranıyor...")

    dest_skus = _fetch_all_skus_with_inventory(dest_api, "Hedef")

    if progress_callback:
        progress_callback(f"Hedef mağazada {len(dest_skus)} varyant bulundu. Eşleştirme yapılıyor...")

    # 2. Match and Calculate Differences
    adjustments = []

    matched_count = 0

    for sku, source_data in source_skus.items():
        if not sku: continue

        dest_data = dest_skus.get(sku)
        if dest_data:
            matched_count += 1
            if dest_data['qty'] != source_data['qty']:
                adjustments.append({
                    "inventoryItemId": dest_data['inventoryItemId'],
                    "availableQuantity": source_data['qty'],
                    "sku": sku,
                    "old_qty": dest_data['qty'],
                    "new_qty": source_data['qty']
                })

    if progress_callback:
        progress_callback(f"{matched_count} SKU eşleşti. {len(adjustments)} stok farkı bulundu. Güncelleniyor...")

    # 3. Apply Updates
    dest_location_id = dest_api.get_default_location_id()

    success_count = 0
    failed_count = 0

    # Use _set_inventory_quantities but with tracking
    chunk_size = 50
    for i in range(0, len(adjustments), chunk_size):
        chunk = adjustments[i:i + chunk_size]

        try:
            _set_inventory_quantities(dest_api, dest_location_id, chunk)
            success_count += len(chunk)
            if progress_callback:
                progress_callback(f"Stok güncelleniyor: {min(i+chunk_size, len(adjustments))}/{len(adjustments)}")
        except Exception as e:
            failed_count += len(chunk)
            logging.error(f"Stok update hatası: {e}")

    return {
        "matched": matched_count,
        "updated": success_count,
        "failed": failed_count,
        "details": adjustments
    }

def _fetch_all_skus_with_inventory(api: ShopifyAPI, label=""):
    """
    Fetches SKU -> {qty, inventoryItemId} map.
    """
    skus = {}
    query = """
    query getAllInventory($cursor: String) {
      products(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            variants(first: 100) {
              edges {
                node {
                  sku
                  inventoryQuantity
                  inventoryItem {
                    id
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {"cursor": None}

    while True:
        data = api.execute_graphql(query, variables)
        products_data = data.get("products", {})

        for edge in products_data.get("edges", []):
            for v_edge in edge["node"].get("variants", {}).get("edges", []):
                node = v_edge["node"]
                sku = node.get("sku")
                if sku:
                    skus[sku.strip()] = {
                        "qty": node.get("inventoryQuantity", 0),
                        "inventoryItemId": node.get("inventoryItem", {}).get("id")
                    }

        if not products_data.get("pageInfo", {}).get("hasNextPage"):
            break
        variables["cursor"] = products_data["pageInfo"]["endCursor"]
        time.sleep(0.5)

    return skus
