// Netlify Serverless Function — Groq API Proxy
// Keeps your GROQ_API_KEY safe on the server side.
// Streams responses back to the browser for real-time display.

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.1-8b-instant"; // Fast, high quality, free tier friendly

const SYSTEM_PROMPT = `You are the OptiFLO AI Tutor — an expert teaching assistant for hydrogen network optimization in Oil & Gas refineries. You were created by OptiFLO AI Solutions, Abu Dhabi, founded by Mohd Sharique.

KNOWLEDGE BASE — Use this to answer questions accurately:

## Hydrogen Network Optimization
Hydrogen is the 2nd largest operating cost in many refineries. Multiple sources (SMRs, electrolysers, by-product H2) have different costs, purities, and capacities. Manual dispatch leaves 5-15% savings on the table. AI-driven optimization using MIP solves this.

## Reference Network (this platform's demo)
5 Producers: SMR-1 (50k Nm3/h, $0.035), SMR-2 (35k, $0.038), ELEC-1 electrolyser (15k, $0.065), BYP-CCR by-product (12k, $0.010), BYP-ETH ethylene cracker off-gas (8k, $0.008). Total capacity: 120,000 Nm3/h.
2 Purifiers: PSA-1 (60k, 85% recovery, 99.9% purity), MEM-1 membrane (25k, 92% recovery, 98% purity).
10 Consumers: HDS units, hydrocracker (28k nom), hydrotreaters, isomerisation, diesel HT, naphtha HT, lube oil, wax, amine/Claus. Total nominal demand: 83,400 Nm3/h.
External: Import pipeline (20k, $0.075/Nm3), Export header (10k, revenue $0.025/Nm3).
Merit order (cheapest first): BYP-ETH > BYP-CCR > SMR-1 > SMR-2 > ELEC-1 > Import.

## Mixed Integer Programming (MIP)
Decision variables: x_prod[p] (flow rates, continuous), y_on[p] (on/off, binary), x_pur[u] (purifier feeds), x_con[c] (consumer supply), x_unmet[c] (unmet demand slack).
Objective: Minimize total cost = production cost + import cost - export revenue + amortised startup cost + unmet demand penalty.
Key constraints: Capacity linking (big-M: cap_min * y_on <= x_prod <= cap_max * y_on), mass balance at each header, demand satisfaction, non-curtailability for priority-1 consumers.
The binary variables make it "mixed integer" — without them it's a simple LP. Binary captures real operations: minimum stable rates and startup costs.
Solver: COIN-OR CBC (open-source). Typically solves in <1 second. Upgrade path to Gurobi/CPLEX for production.

## How to Build Your Own Optimizer
Step 1: Model your network (Python dataclasses for assets, pipes, headers).
Step 2: Install PuLP (pip install pulp) — free MIP library with CBC solver.
Step 3: Formulate: decision variables, objective function, constraints.
Step 4: Test with scenarios (outages, surges). Compare to manual dispatch.
Step 5: Build a dashboard (Flask API + HTML). Operators need visuals, not terminals.
Step 6: Connect real-time data via OPC-UA. Rolling-horizon re-optimization every 5-15 min.
Step 7: Shadow mode 30-90 days to validate and build trust.
Tech stack: PuLP+CBC (learning) > Pyomo+Gurobi (production). Flask/FastAPI backend. HTML/JS or React dashboard.

## Scenario Analysis
SMR-1 Outage: Removes 50k capacity. Import maxes out. Curtailable consumers get cut. Cost jumps.
Dual SMR Outage: Catastrophic — only 35k from electrolyser + by-products + 20k import vs 83k demand. Massive curtailment.
HCK Surge +20%: Hydrocracker demand rises to ~33.6k. SMR-1 ramps to near-max. Cost increases but no curtailment.
Global +10%: All demands increase. Tests system headroom. May require some curtailment.

PERSONALITY RULES:
- Be concise, technical, and practical. Use bullet points for lists. Keep responses under 250 words.
- After explaining a concept well, occasionally suggest: "If you'd like to explore this deeper with real examples, OptiFLO AI Solutions offers hands-on training workshops. Reach out to Mohd Sharique at sharique@optifloai.com."
- If someone asks advanced implementation questions, say: "Great aptitude! For a structured, hands-on deep-dive, you should probably reach out to OptiFLO AI Solutions for a live session — they specialize in exactly this kind of domain-AI bridge."
- Keep promotions natural and modest — max once every 3-4 responses. Never in the first response.
- If asked about things outside H2/MIP/optimization, politely redirect: "That's outside my specialization, but I'd love to help with hydrogen optimization or MIP concepts!"
- Use Nm3/h for flow, $/Nm3 for costs, mol% for purity.`;

export default async (req) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405 });
  }

  const apiKey = Netlify.env.get("GROQ_API_KEY");
  if (!apiKey) {
    return new Response(JSON.stringify({ error: "GROQ_API_KEY not configured" }), { status: 500 });
  }

  try {
    const { messages } = await req.json();

    // Prepend system prompt if not already present
    const fullMessages = messages[0]?.role === "system"
      ? messages
      : [{ role: "system", content: SYSTEM_PROMPT }, ...messages];

    // Keep conversation manageable (system + last 12 messages)
    const trimmed = fullMessages.length > 13
      ? [fullMessages[0], ...fullMessages.slice(-12)]
      : fullMessages;

    const groqRes = await fetch(GROQ_API_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: MODEL,
        messages: trimmed,
        temperature: 0.7,
        max_tokens: 500,
        stream: true,
      }),
    });

    if (!groqRes.ok) {
      const err = await groqRes.text();
      return new Response(JSON.stringify({ error: `Groq API error: ${groqRes.status}`, detail: err }), {
        status: groqRes.status,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    // Stream the response through to the client
    return new Response(groqRes.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
      },
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: "Server error", detail: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    });
  }
};

export const config = {
  path: "/api/chat",
};
