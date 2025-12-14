# Quick Setup Checklist for Shopify Embedded App

## 📋 Pre-Deployment Checklist

### ✅ 1. Shopify Partner Account Setup
- [ ] Created Shopify Partner account at [partners.shopify.com](https://partners.shopify.com/)
- [ ] Created new app in Partner Dashboard
- [ ] Noted down **API Key** (Client ID)
- [ ] Noted down **API Secret** (Client Secret)
- [ ] Enabled "Embedded app" in app settings

### ✅ 2. Local Environment Setup
- [ ] Copied `.env.example` to `.env`
- [ ] Added `SHOPIFY_API_KEY` to `.env`
- [ ] Added `SHOPIFY_API_SECRET` to `.env`
- [ ] Generated `SESSION_SECRET` using: `openssl rand -hex 32`
- [ ] Set `APP_URL=http://localhost:8000` for local testing

### ✅ 3. Local Testing
- [ ] Installed Docker Desktop
- [ ] Ran `./test-local.sh` successfully
- [ ] App loads at `http://localhost:8000`
- [ ] No errors in terminal output

### ✅ 4. Render Account Setup
- [ ] Created account at [render.com](https://render.com/)
- [ ] Connected GitHub account
- [ ] Repository is pushed to GitHub

### ✅ 5. Render Deployment
- [ ] Created new Web Service
- [ ] Selected Docker environment
- [ ] Set Environment Variables:
  - [ ] `SHOPIFY_API_KEY`
  - [ ] `SHOPIFY_API_SECRET`
  - [ ] `APP_URL=https://your-app.onrender.com`
  - [ ] `SHOPIFY_SCOPES=read_products,write_products,read_orders`
  - [ ] `SESSION_SECRET` (generated)
- [ ] Set Health Check Path to `/health`
- [ ] Clicked "Create Web Service"
- [ ] Waited for first deployment (5-10 minutes)
- [ ] Verified health check passes: `https://your-app.onrender.com/health`

### ✅ 6. Shopify App Configuration
- [ ] Updated **App URL** to: `https://your-app.onrender.com/app`
- [ ] Updated **Allowed redirection URLs** to: `https://your-app.onrender.com/auth/callback`
- [ ] Saved changes in Partner Dashboard

### ✅ 7. Installation Testing
- [ ] Visited: `https://your-app.onrender.com/auth/shopify?shop=your-store.myshopify.com`
- [ ] Successfully completed OAuth flow
- [ ] App loads inside Shopify admin
- [ ] No iframe blocking errors
- [ ] Polaris styling applied correctly
- [ ] App Bridge toast notifications work

### ✅ 8. Production Checklist
- [ ] Changed default password in `auth.py` or disabled demo auth
- [ ] Implemented proper user authentication
- [ ] Set up database for storing access tokens (not session-based)
- [ ] Configured UptimeRobot to prevent cold starts
- [ ] Added error monitoring (e.g., Sentry)
- [ ] Reviewed and minimized required OAuth scopes
- [ ] Tested on multiple Shopify stores
- [ ] Added GDPR compliance features (data deletion webhook)
- [ ] Submitted app for review (if publishing to App Store)

## 🚨 Common Issues & Solutions

### Issue: "Refused to frame" error
**Solution**: Check CSP headers in `main.py` - ensure shop domain is included

### Issue: OAuth callback fails with 400 error
**Solution**: Verify SHOPIFY_API_SECRET is correct and callback URL matches exactly

### Issue: App loads but styling is wrong
**Solution**: Ensure `inject_shopify_style()` is called at the top of each page

### Issue: Render service fails to start
**Solution**: Check logs in Render dashboard, verify all env vars are set

### Issue: Cold start takes too long
**Solution**: Set up UptimeRobot to ping `/health` every 5 minutes

## 🎯 Next Steps After Deployment

1. **Monitor Performance**
   - Check Render logs daily
   - Set up error alerts
   - Monitor response times

2. **Enhance Security**
   - Move to database-backed token storage
   - Implement token refresh logic
   - Add rate limiting
   - Set up webhook verification for all endpoints

3. **Add Features**
   - Implement all your Streamlit pages
   - Add bulk operations
   - Create analytics dashboards
   - Set up scheduled syncs

4. **Prepare for Production**
   - Write comprehensive tests
   - Document API endpoints
   - Create user documentation
   - Set up backup systems

5. **Scale When Ready**
   - Upgrade Render plan for always-on service
   - Add PostgreSQL database
   - Implement caching with Redis
   - Set up CDN for static assets

## 📚 Resources

- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Full documentation
- [Shopify App Documentation](https://shopify.dev/docs/apps)
- [Render Documentation](https://render.com/docs)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Questions?** Check the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) or open an issue on GitHub.
