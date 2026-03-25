# Netlify Deployment Guide — OptiFLO AI Learning Platform

## Step 0: Get a Free Groq API Key (AI Chatbot)

The AI Tutor chatbot is powered by Groq's Llama 3 API (free tier, no credit card needed).

1. Go to **https://console.groq.com** and sign up
2. Navigate to **API Keys** → **Create API Key**
3. Copy the key (starts with `gsk_...`) — you'll need it in Step 2

**Free tier limits:** ~30 requests/minute, ~14,400/day — more than enough for your platform.

## Step 1: Set Up Formspree (Feedback Form)

1. Go to **https://formspree.io** and create a free account
2. Create a new form — Formspree will give you an endpoint like `https://formspree.io/f/xYzAbCdE`
3. Open `index.html`, search for `xplaceholder`, and replace it with your Formspree form ID (appears once in the JavaScript fetch call)
4. Save the file

**What you'll get:** Emails at sharique@optifloai.com with name, email, org, role, and feedback.

## Step 2: Prepare Your Deployment Folder

You need to create a clean folder on your Desktop with ONLY the files Netlify needs. Here is exactly what to do:

### 2A. Create the folder on your computer

1. On your Desktop, create a new folder called `optiflo-ai`
2. COPY these 2 items into it from your current project folder:
   - `index.html` (the platform file)
   - `netlify` folder (which contains `functions/chat.mjs` — the AI chatbot backend)

3. Your folder should look EXACTLY like this when done:

```
Desktop/
  optiflo-ai/
    index.html
    netlify/
      functions/
        chat.mjs
```

That's it — just 2 things inside `optiflo-ai`: the HTML file and the `netlify` folder.

**DO NOT** copy the Python files, markdown files, or anything else. Netlify only needs these 2 items.

### 2B. Sign up on Netlify

1. Open your browser and go to **https://app.netlify.com**
2. Click **"Sign up"** — you can sign up with your GitHub account or email
3. It's free, no credit card needed

### 2C. Deploy your folder (Drag & Drop method)

1. After logging in, you'll see the Netlify dashboard
2. Click the **"Add new site"** button (top area of the page)
3. Select **"Deploy manually"**
4. You'll see a large dotted rectangle that says "Drag and drop your site output folder here"
5. Open your Desktop in File Explorer, find the `optiflo-ai` folder
6. **Drag the ENTIRE `optiflo-ai` folder** and drop it onto that dotted rectangle
7. Wait 10-20 seconds — Netlify will deploy your site
8. You'll get a live URL like `https://sunny-dolphin-a1b2c3.netlify.app`

### 2D. Add your Groq API Key (IMPORTANT — chatbot won't work without this)

1. On your Netlify dashboard, click on your newly deployed site
2. Click **"Site configuration"** in the left sidebar
3. Click **"Environment variables"**
4. Click **"Add a variable"**
5. In the **Key** field, type exactly: `GROQ_API_KEY`
6. In the **Value** field, paste your Groq API key (the one starting with `gsk_...` from Step 0)
7. Click **"Save"**

### 2E. Redeploy (required after adding the environment variable)

1. Go back to your site's **"Deploys"** tab
2. Click **"Trigger deploy"** → **"Deploy site"**
3. Wait for it to finish (10-20 seconds)
4. Your site is now live with the chatbot working!

### 2F. Rename your site URL (optional but recommended)

1. Go to **"Site configuration"** → **"Site details"**
2. Click **"Change site name"**
3. Type a clean name like `optiflo-ai`
4. Your URL becomes: `https://optiflo-ai.netlify.app`

## Step 3: Custom Domain (Optional)

1. In Netlify site settings → **"Domain management"** → **"Add custom domain"**
2. Suggestion: `optiflo-ai.netlify.app` (free) or `optifloai.com` (purchased)
3. Rename via: Site settings → **"Change site name"** → e.g., `optiflo-ai`

## Step 4: Visitor Analytics

### Free: GoatCounter (Recommended)

Add this to `index.html` just before `</body>`:

```html
<script data-goatcounter="https://optifloai.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
```

Setup:
1. Go to **https://www.goatcounter.com** and create an account with code `optifloai`
2. Dashboard at `https://optifloai.goatcounter.com` — shows visitors, pages, referrers

### Paid: Netlify Analytics ($9/month)

Netlify dashboard → **"Analytics"** — no cookies, no client-side JS.

## Step 5: Update LinkedIn Post

Replace `[INSERT YOUR NETLIFY URL]` in LINKEDIN_POST.md with your deployed URL.

## Checklist Before Publishing

- [ ] Groq API key obtained from console.groq.com
- [ ] GROQ_API_KEY added as Netlify environment variable
- [ ] Formspree form ID replaced in index.html (search for `xplaceholder`)
- [ ] Folder deployed to Netlify (index.html + netlify/functions/chat.mjs)
- [ ] Test the chatbot — click "Start Learning", ask a question
- [ ] Test the feedback form — submit a test entry, check email
- [ ] GoatCounter or Netlify Analytics set up
- [ ] LinkedIn post updated with actual URL
- [ ] Tested on mobile
- [ ] Tried all 6 optimizer scenarios
- [ ] Tried "Build Your Own Network" feature
- [ ] Screenshot taken for LinkedIn post image

## Troubleshooting

**Chatbot says "API error 401":** Your GROQ_API_KEY is missing or wrong. Check Netlify environment variables.

**Chatbot says "API error 429":** Rate limit hit. Free tier allows ~30 req/min. Wait a minute and retry.

**Chatbot works locally but not on Netlify:** Make sure the `netlify/functions/chat.mjs` file is deployed and the environment variable is set. Redeploy after adding the variable.

**Feedback form doesn't send:** Replace `xplaceholder` in index.html with your actual Formspree form ID.
