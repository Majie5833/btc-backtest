# 第九账户「扫荡空」(SweepShort)：日线空头趋势 + 4H扫上影做空（无未来函数）
# 规则: 4H收盘<EMA200 且 EMA20<EMA50(下跌趋势) + 当前bar最高刺破前bar高点但收盘收回下方且收阴
#       → 下根4H开盘做空; SL=反抽高点+0.5×ATR14; TP=2R固定; 宽度>3×ATR放弃
# 风险0.75%; 连亏3笔×0.5; 费0.05%+滑点0.02%
# 3.7年回测: 130笔 45%×1.96 +74.5% 最大DD 11.3% (2023:+945 2024:-375 2025:+3555 2026:+3295)
FEES=0.0005; SLIP=0.0002; RISK=0.0075
OBSERVE_ONLY=True  # 交叉验证发现真实期望≈-13%(+74.5%系当时扫描脚本bug), 降级为观察账户: 只平不开

def _ema(vals,n):
    k=2/(n+1); out=[vals[0]]
    for v in vals[1:]: out.append(out[-1]*(1-k)+v*k)
    return out

def _atrs(h,l,c,n=14):
    out=[]
    for i in range(len(c)):
        pc=c[i-1] if i>0 else c[0]
        tr=max(h[i]-l[i],abs(h[i]-pc),abs(l[i]-pc))
        out.append(tr if i==0 else out[-1]*(n-1)/n+tr/n)
    return out

def prep(c4):
    # c4行: [ts,o,h,l,c,vol]
    h=[x[2] for x in c4]; l=[x[3] for x in c4]; c=[x[4] for x in c4]
    return {"h":h,"l":l,"c":c,"o":[x[1] for x in c4],"ts":[x[0] for x in c4],
            "e200":_ema(c,200),"e20":_ema(c,20),"e50":_ema(c,50),"atr":_atrs(h,l,c)}

def step(acct,P,i,events):
    a=acct
    a.setdefault("pos",None); a.setdefault("trades",[])
    a.setdefault("loss_streak",0); a.setdefault("risk_factor",1.0)
    if i<210 or i>=len(P["c"])-1: return
    h,l,c,o=P["h"],P["l"],P["c"],P["o"]
    pos=a["pos"]
    # ---- 持仓管理(空头): 同bar先查SL(保守) ----
    if pos:
        rf=1-FEES-SLIP
        pnl=None
        if h[i+1]>=pos["sl"]:
            pnl=pos["qty"]*(pos["entry"]-pos["sl"])*rf
            ev="止损"
        elif l[i+1]<=pos["tp"]:
            pnl=pos["qty"]*(pos["entry"]-pos["tp"])*rf
            ev="止盈2R"
        if pnl is not None:
            import time as _t
            a["eq"]=round(a["eq"]+pnl,2)
            a["trades"].append({"ts":P["ts"][i+1],"pnl":round(pnl,2),"ev":ev,
                                "entry":pos["entry"],"sl":pos["sl"],"tp":pos["tp"]})
            if pnl<0:
                a["loss_streak"]+=1
                a["risk_factor"]=0.5 if a["loss_streak"]>=3 else 1.0
            else:
                a["loss_streak"]=0; a["risk_factor"]=1.0
            events.append(f"[扫荡空] {ev} {'+' if pnl>=0 else ''}${pnl:.2f} 净值${a['eq']:,.0f}")
            a["pos"]=None
        return
    # ---- 开仓条件 ----
    if OBSERVE_ONLY: return
    if not (c[i]<P["e200"][i] and P["e20"][i]<P["e50"][i]): return
    ph=h[i-1]
    if not (h[i]>ph and c[i]<ph and c[i]<o[i]): return
    stop=h[i]+0.5*P["atr"][i]; w=stop-c[i]
    if w<=0 or w>3*P["atr"][i]: return
    entry=o[i+1]; qty=a["eq"]*RISK*a["risk_factor"]/w
    a["pos"]={"dir":-1,"entry":entry,"sl":stop,"tp":c[i]-2*w,"qty":qty,"rd":w,
              "tag":"扫荡空","be":False}
    events.append(f"[扫荡空] 扫上影做空 @${entry:,.0f} SL ${stop:,.0f} TP ${c[i]-2*w:,.0f}")
