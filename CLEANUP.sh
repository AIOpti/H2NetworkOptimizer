#!/bin/bash
# OptiFLO AI — Project Cleanup Script
# Run this to organize the folder before deployment

echo "=== OptiFLO AI Folder Cleanup ==="

# Create docs folder for reference materials
mkdir -p docs

# Move documentation files to docs/
mv -f LINKEDIN_POST.md docs/ 2>/dev/null
mv -f LinkedinPost.docx docs/ 2>/dev/null
mv -f OptiFLO_AI_Platform_Guide.doc docs/ 2>/dev/null
mv -f BENCHMARK_VALIDATION.md docs/ 2>/dev/null
mv -f H2_OptiNet_Concept_Document.md docs/ 2>/dev/null
mv -f NETLIFY_DEPLOYMENT_GUIDE.md docs/ 2>/dev/null

# Remove superseded Python backend files (replaced by single HTML app)
rm -f app.py optimizer.py network_config.py data_generator.py dashboard.html requirements.txt
rm -rf __pycache__

# Remove temp/lock files
rm -f ~WRL*.tmp ~\$*.docx test.txt SESSION_STATUS.md

# Remove the Groq API key from index.html before pushing
# IMPORTANT: uncomment the next line before deploying to production
# sed -i 's/const GROQ_DIRECT_KEY="gsk_[^"]*"/const GROQ_DIRECT_KEY=""/' index.html

echo ""
echo "=== Final structure ==="
echo "index.html          — Main app (deploy this)"
echo "netlify/functions/   — Serverless function (chat proxy)"
echo "docs/                — Reference documents"
echo ".gitignore           — Git ignore rules"
echo ""
echo "=== Ready for deployment ==="
echo "git add index.html netlify/ .gitignore docs/"
echo "git commit -m 'Clean deployment: OptiFLO AI platform'"
echo "git push"
