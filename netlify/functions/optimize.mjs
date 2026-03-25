// Netlify Serverless Function — H2 Network Optimizer (Server-Side)
// Keeps solver logic protected from client-side reverse engineering.

// ── Network Data ────────────────────────────────────────────────────────────
const NET = {
  producers: {
    "SMR-1":{name:"Steam Methane Reformer #1",type:"SMR",min:8000,max:50000,cost:0.035,startup:15000,co2:0.27},
    "SMR-2":{name:"Steam Methane Reformer #2",type:"SMR",min:5000,max:35000,cost:0.038,startup:12000,co2:0.27},
    "ELEC-1":{name:"PEM Electrolyser",type:"Electrolyser",min:1000,max:15000,cost:0.065,startup:500,co2:0.02},
    "BYP-CCR":{name:"CCR By-product H\u2082",type:"ByProduct",min:3000,max:12000,cost:0.010,startup:0,co2:0},
    "BYP-ETH":{name:"Ethylene Cracker Off-gas",type:"ByProduct",min:2000,max:8000,cost:0.008,startup:0,co2:0},
  },
  consumers: {
    "C-HDS1":{name:"HDS Unit 1",nom:14000,max:18000,pri:1,curt:false,pen:0.20},
    "C-HDS2":{name:"HDS Unit 2",nom:9000,max:12000,pri:1,curt:false,pen:0.20},
    "C-HCK":{name:"Hydrocracker",nom:28000,max:35000,pri:1,curt:false,pen:0.25},
    "C-HTR":{name:"Hydrotreater",nom:7500,max:10000,pri:2,curt:false,pen:0.15},
    "C-ISO":{name:"Isomerisation",nom:3000,max:4000,pri:2,curt:true,pen:0.10},
    "C-DHT":{name:"Diesel HT",nom:11000,max:15000,pri:1,curt:false,pen:0.18},
    "C-NHT":{name:"Naphtha HT",nom:5500,max:8000,pri:3,curt:true,pen:0.08},
    "C-LUB":{name:"Lube Oil HT",nom:2200,max:3500,pri:3,curt:true,pen:0.12},
    "C-WAX":{name:"Wax Hydrofinisher",nom:1200,max:2000,pri:4,curt:true,pen:0.06},
    "C-H2S":{name:"Amine/Claus Feed",nom:2000,max:3000,pri:5,curt:true,pen:0.04},
  },
  import:{max:20000,cost:0.075},
  export:{max:10000,revenue:0.025}
};

// ── Solvers ─────────────────────────────────────────────────────────────────

function solveMeritOrder(producers, consumers, imp, exp, customHpcIds, purCfg) {
  const sorted = Object.entries(producers).sort((a,b)=>a[1].cost-b[1].cost);
  const totalDemand = Object.values(consumers).reduce((s,c)=>s+c.nom,0);

  const defaultHpc = ["C-HTR","C-NHT","C-WAX","C-H2S"];
  const hpcIds = customHpcIds || defaultHpc;
  const uhpIds = Object.keys(consumers).filter(id=>!hpcIds.includes(id));
  const uhpDemand = uhpIds.reduce((s,id)=>s+consumers[id].nom,0);
  const hpcDemand = hpcIds.reduce((s,id)=>s+(consumers[id]?consumers[id].nom:0),0);

  const PSA_SPLIT = purCfg ? purCfg.psaSplit : 0.70;
  const PSA_REC   = purCfg ? purCfg.psaRec   : 0.85;
  const PSA_MAX   = purCfg ? purCfg.psaMax   : 60000;
  const MEM_REC   = purCfg ? purCfg.memRec   : 0.92;
  const MEM_MAX   = purCfg ? purCfg.memMax   : 25000;
  const MEM_SPLIT = 1 - PSA_SPLIT;

  const psaEffective = PSA_SPLIT * PSA_REC;
  const memEffective = MEM_SPLIT * MEM_REC;
  const reqForUHP = uhpDemand > 0 ? uhpDemand / psaEffective : 0;
  const reqForHPC = hpcDemand > 0 ? hpcDemand / memEffective : 0;
  const requiredHP = reqForUHP + reqForHPC;
  const dispatchFactor = requiredHP > 0 ? Math.max(totalDemand / requiredHP, 0.40) : (psaEffective+memEffective);

  let r={prodFlows:{},prodOn:{},consSupplied:{},consUnmet:{},importFlow:0,exportFlow:0,costs:{production:0,import:0,export_revenue:0,startup:0,unmet_penalty:0,total:0},purFeeds:{"PSA-1":0,"MEM-1":0},crossTier:{},importAlloc:{}};
  let hpSupply=0,uhpDirect=0;

  for(const[pid,p]of sorted){
    let needed=totalDemand-hpSupply*dispatchFactor-uhpDirect-r.importFlow;
    if(needed<=0){r.prodFlows[pid]=0;r.prodOn[pid]=false;continue}
    let flow=Math.min(p.max,Math.max(p.min,needed*1.05));
    flow=Math.max(p.min,Math.min(p.max,flow));
    r.prodFlows[pid]=flow;r.prodOn[pid]=true;
    r.costs.production+=p.cost*flow;
    if(pid==="ELEC-1")uhpDirect+=flow; else hpSupply+=flow;
  }

  let psaFeed=Math.min(hpSupply*PSA_SPLIT, PSA_MAX);
  let memFeed=Math.min(hpSupply*MEM_SPLIT, MEM_MAX);
  let overflow=hpSupply-psaFeed-memFeed;
  if(overflow>0){
    const psaRoom=PSA_MAX-psaFeed;
    const memRoom=MEM_MAX-memFeed;
    const toPSA=Math.min(overflow,psaRoom);
    psaFeed+=toPSA; overflow-=toPSA;
    const toMEM=Math.min(overflow,memRoom);
    memFeed+=toMEM; overflow-=toMEM;
  }
  r.purFeeds={"PSA-1":psaFeed,"MEM-1":memFeed};
  r.purBypass=overflow;
  const psaOut=psaFeed*PSA_REC;
  const psaLoss=psaFeed*(1-PSA_REC);
  const memOut=memFeed*MEM_REC;
  const memLoss=memFeed*(1-MEM_REC);
  r.psaOut=psaOut; r.psaLoss=psaLoss;
  r.memOut=memOut; r.memLoss=memLoss;
  let uhpAvail=psaOut+uhpDirect;
  let hpcAvail=memOut+overflow;

  const sortedCons=Object.entries(consumers).sort((a,b)=>a[1].pri-b[1].pri);
  for(const[cid,c]of sortedCons){
    if(!uhpIds.includes(cid)) continue;
    const supply=Math.min(c.nom,uhpAvail);
    r.consSupplied[cid]=supply;
    r.consUnmet[cid]=Math.max(0,c.nom-supply);
    uhpAvail-=supply;
  }

  let hpcRemain=hpcAvail;
  for(const[cid,c]of sortedCons){
    if(uhpIds.includes(cid)) continue;
    const supply=Math.min(c.nom,hpcRemain);
    r.consSupplied[cid]=supply;
    r.consUnmet[cid]=Math.max(0,c.nom-supply);
    hpcRemain-=supply;
  }

  if(uhpAvail>0){
    for(const[cid,c]of sortedCons){
      if(uhpIds.includes(cid)) continue;
      const unmet=r.consUnmet[cid];
      if(unmet<=0) continue;
      const extra=Math.min(unmet,uhpAvail);
      r.consSupplied[cid]+=extra;
      r.consUnmet[cid]-=extra;
      r.crossTier[cid]=extra;
      uhpAvail-=extra;
      if(uhpAvail<=0) break;
    }
  }

  let totalUnmet=0;
  for(const[cid] of sortedCons) totalUnmet+=r.consUnmet[cid];
  if(totalUnmet>0){
    r.importFlow=Math.min(totalUnmet,imp.max);
    r.costs.import=imp.cost*r.importFlow;
    let importRemain=r.importFlow;
    for(const[cid,c]of sortedCons){
      const unmet=r.consUnmet[cid];
      if(unmet<=0||importRemain<=0) continue;
      const fill=Math.min(unmet,importRemain);
      r.consSupplied[cid]+=fill;
      r.consUnmet[cid]-=fill;
      r.importAlloc[cid]=fill;
      importRemain-=fill;
    }
  }

  for(const[cid,c]of sortedCons){
    if(r.consUnmet[cid]>0) r.costs.unmet_penalty+=c.pen*r.consUnmet[cid];
  }

  const totalSurplus=uhpAvail+hpcRemain;
  if(totalSurplus>0){r.exportFlow=Math.min(totalSurplus,exp.max);r.costs.export_revenue=exp.revenue*r.exportFlow}
  r.costs.total=r.costs.production+r.costs.import-r.costs.export_revenue+r.costs.unmet_penalty;
  return r;
}

function solveDirectSupply(producers, consumers, imp, exp) {
  const sorted = Object.entries(producers).sort((a,b)=>a[1].cost-b[1].cost);
  const totalDemand = Object.values(consumers).reduce((s,c)=>s+c.nom,0);
  let r={prodFlows:{},prodOn:{},consSupplied:{},consUnmet:{},importFlow:0,exportFlow:0,
    costs:{production:0,import:0,export_revenue:0,startup:0,unmet_penalty:0,total:0},purFeeds:{"PSA-1":0,"MEM-1":0}};
  let totalSupply=0;
  for(const[pid,p]of sorted){
    const remaining=totalDemand-totalSupply;
    if(remaining<=0){r.prodFlows[pid]=0;r.prodOn[pid]=false;continue}
    let flow;
    if(remaining<p.min){flow=p.min}
    else{flow=Math.min(p.max,Math.max(p.min,remaining))}
    flow=Math.max(p.min,Math.min(p.max,flow));
    r.prodFlows[pid]=flow; r.prodOn[pid]=true;
    r.costs.production+=p.cost*flow;
    totalSupply+=flow;
  }
  let deficit=totalDemand-totalSupply;
  if(deficit>0){r.importFlow=Math.min(deficit,imp.max);totalSupply+=r.importFlow;r.costs.import=imp.cost*r.importFlow}
  let avail=totalSupply;
  const sortedCons=Object.entries(consumers).sort((a,b)=>a[1].pri-b[1].pri);
  for(const[cid,c]of sortedCons){
    const supply=Math.min(c.nom,avail);
    r.consSupplied[cid]=supply;
    const unmet=Math.max(0,c.nom-supply);
    r.consUnmet[cid]=unmet;
    avail-=supply;
    if(unmet>0)r.costs.unmet_penalty+=c.pen*unmet;
  }
  if(avail>0){r.exportFlow=Math.min(avail,exp.max);r.costs.export_revenue=exp.revenue*r.exportFlow}
  r.costs.total=r.costs.production+r.costs.import-r.costs.export_revenue+r.costs.unmet_penalty;
  return r;
}

// ── Scenario Logic ──────────────────────────────────────────────────────────

function getScenarioInputs(name) {
  let p=JSON.parse(JSON.stringify(NET.producers)), c=JSON.parse(JSON.stringify(NET.consumers));
  switch(name){
    case'smr1_outage':p["SMR-1"].max=0;p["SMR-1"].min=0;break;
    case'smr2_outage':p["SMR-2"].max=0;p["SMR-2"].min=0;break;
    case'dual_smr_outage':p["SMR-1"].max=0;p["SMR-1"].min=0;p["SMR-2"].max=0;p["SMR-2"].min=0;break;
    case'hck_surge':c["C-HCK"].nom=33600;c["C-HCK"].max=42000;break;
    case'global_surge':Object.values(c).forEach(x=>{x.nom=Math.round(x.nom*1.1);x.max=Math.round(x.max*1.1)});break;
  }
  return {p,c};
}

// ── CORS ────────────────────────────────────────────────────────────────────

const ALLOWED_ORIGINS = [
  "https://optifloai.netlify.app",
  "https://h2networkoptimizer.netlify.app",
  "http://localhost:8888",
  "http://localhost:3000",
];

function getCorsOrigin(req) {
  const origin = req.headers.get("Origin") || "";
  if (ALLOWED_ORIGINS.some(o => origin.startsWith(o))) return origin;
  // Allow any netlify.app subdomain
  if (origin.endsWith(".netlify.app")) return origin;
  return ALLOWED_ORIGINS[0];
}

// ── Handler ─────────────────────────────────────────────────────────────────

export default async (req) => {
  const corsOrigin = getCorsOrigin(req);
  const corsHeaders = {
    "Access-Control-Allow-Origin": corsOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const body = await req.json();
    const { mode } = body;
    let result;

    if (mode === "reference") {
      // Reference network scenario
      const { scenario } = body;
      const { p, c } = getScenarioInputs(scenario || "base");
      result = solveMeritOrder(p, c, NET.import, NET.export);

    } else if (mode === "custom") {
      // Custom network from builder
      const { producers, consumers, importCfg, exportCfg, usePurifiers, customHpcIds, purCfg } = body;
      if (!producers || !consumers) {
        return new Response(JSON.stringify({ error: "producers and consumers required" }), {
          status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      const imp = importCfg || { max: 15000, cost: 0.075 };
      const exp = exportCfg || { max: 5000, revenue: 0.025 };
      result = usePurifiers
        ? solveMeritOrder(producers, consumers, imp, exp, customHpcIds || null, purCfg || null)
        : solveDirectSupply(producers, consumers, imp, exp);

    } else if (mode === "compare") {
      // Compare two reference scenarios
      const { scenarioA, scenarioB } = body;
      const { p: pA, c: cA } = getScenarioInputs(scenarioA || "base");
      const { p: pB, c: cB } = getScenarioInputs(scenarioB || "base");
      const rA = solveMeritOrder(pA, cA, NET.import, NET.export);
      const rB = solveMeritOrder(pB, cB, NET.import, NET.export);
      result = { resultA: rA, resultB: rB };

    } else if (mode === "sensitivity") {
      // Sensitivity analysis — 11 steps, server-side batch
      const { param } = body;
      const steps = 11, results = [];
      for (let i = 0; i < steps; i++) {
        const factor = 0.5 + (i / (steps - 1));
        const p = JSON.parse(JSON.stringify(NET.producers));
        const c = JSON.parse(JSON.stringify(NET.consumers));
        let baseVal = 0;
        switch (param) {
          case 'smr1_cost': baseVal=p["SMR-1"].cost; p["SMR-1"].cost=baseVal*factor; break;
          case 'smr2_cost': baseVal=p["SMR-2"].cost; p["SMR-2"].cost=baseVal*factor; break;
          case 'elec1_cost': baseVal=p["ELEC-1"].cost; p["ELEC-1"].cost=baseVal*factor; break;
          case 'import_cost': baseVal=NET.import.cost; break;
          case 'hck_demand': baseVal=c["C-HCK"].nom; c["C-HCK"].nom=Math.round(baseVal*factor); c["C-HCK"].max=Math.round(c["C-HCK"].max*factor); break;
          case 'global_demand': Object.values(c).forEach(x=>{x.nom=Math.round(x.nom*factor);x.max=Math.round(x.max*factor)}); baseVal=83400; break;
        }
        const impCfg = { max: NET.import.max, cost: param === 'import_cost' ? NET.import.cost * factor : NET.import.cost };
        const r = solveMeritOrder(p, c, impCfg, NET.export);
        results.push({ factor, cost: r.costs.total, import: r.importFlow, penalty: r.costs.unmet_penalty, prod: r.costs.production });
      }
      result = { results };

    } else {
      return new Response(JSON.stringify({ error: "Invalid mode. Use: reference, custom, compare, or sensitivity" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify(result), {
      status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });

  } catch (err) {
    console.error("Optimize error:", err);
    return new Response(JSON.stringify({ error: "Optimization failed" }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
};

export const config = {
  path: "/api/optimize",
};
