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

## Step 2: Deploy to Netlify (with Serverless Functions)

The chatbot requires a Netlify Function to proxy API calls securely. This means you need to deploy a **folder** (not just the HTML file).

### Your folder structure should be:
```
optiflo-ai/
├── index.html                    ← the platform
└── netlify/
    └── functions/
        └── chat.mjs              ← Groq API proxy (serverless function)
```

### Deploy via GitHub (Recommended)

1. Create a GitHub repository (e.g., `optiflo-ai`)
2. Upload the folder structure above to the repo
3. In Netlify: **"Add new site"** → **"Import an existing project"** → Select your GitHub repo
4. Build settings: Leave everything blank (no build command needed)
5. Click **Deploy**

### Add your Groq API Key as Environment Variable

**CRITICAL — do this before the chatbot will work:**

1. In your Netlify site dashboard → **"Site configuration"** → **"Environment variables"**
2. Click **"Add a variable"**
3. Key: `GROQ_API_KEY`
4. Value: paste your Groq API key (`gsk_...`)
5. Save

The serverless function reads this key server-side — it's never exposed to visitors.

### Deploy via Drag & Drop (Quick Test)

1. Create the folder structure above on your computer
2. Go to **https://app.netlify.com** → **"Add new site"** → **"Deploy manually"**
3. Drag the **entire folder** (not just index.html) into the upload area
4. Then add the GROQ_API_KEY environment variable as described above

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
