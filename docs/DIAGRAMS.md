# Mermaid diagrams for the methodology document

Orange marks the intervention, what follows from it, and the cells holding
the result. Everything else is grey.

All numbers come from seed 7 and from `runs/`, checked against the code at
`594038c`, not transcribed from the document.

---

## 1. Redirect on seed 7, before and after

The optimal route is orange, T\* is the darkest edge on it, off-route links
are grey.

```mermaid
flowchart LR
  E(["E — start"]) ==>|"a1 0.64"| C(["C"])
  C ==>|"a2 0.73"| D(["D"])
  D ==>|"T* a2 0.62"| B(["B"])
  B ==>|"a2 0.63"| F(["F — goal"])
  D -->|"a1 0.79"| A(["A"])
  H(["H"]) -->|"a1 0.80"| B

  classDef route fill:#FFE8D6,stroke:#E8590C,stroke-width:2.5px,color:#7A2E0E
  classDef target fill:#E8590C,stroke:#9A3412,stroke-width:3px,color:#FFFFFF
  classDef off fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#9CA3AF
  class E,C,B,F route
  class D target
  class A,H off
  linkStyle 0,1,3 stroke:#E8590C,stroke-width:3px
  linkStyle 2 stroke:#9A3412,stroke-width:6px
  linkStyle 4,5 stroke:#D1D5DB,stroke-width:1px
```

**Before, M0.** Best route E, C, D, B, F at cost 6.13. The thick dark edge is
T\*: node D, action a2, probability 0.62, landing on B.

```mermaid
flowchart LR
  E(["E — start"]) ==>|"a1 0.64"| C(["C"])
  C ==>|"a2 0.73"| D(["D"])
  D ==>|"T* a2 0.62"| H(["H"])
  H ==>|"a1 0.80"| B(["B"])
  B ==>|"a2 0.63"| F(["F — goal"])
  D -->|"a1 0.79"| A(["A"])

  classDef route fill:#FFE8D6,stroke:#E8590C,stroke-width:2.5px,color:#7A2E0E
  classDef target fill:#E8590C,stroke:#9A3412,stroke-width:3px,color:#FFFFFF
  classDef moved fill:#FFFFFF,stroke:#E8590C,stroke-width:3px,color:#7A2E0E
  classDef off fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#9CA3AF
  class E,C,B,F route
  class D target
  class H moved
  class A off
  linkStyle 0,1,3,4 stroke:#E8590C,stroke-width:3px
  linkStyle 2 stroke:#9A3412,stroke-width:6px
  linkStyle 5 stroke:#D1D5DB,stroke-width:1px
```

**After, M1.** Same action, same 0.62, now landing on H. The route lengthens
to E, C, D, H, B, F at cost 7.38. H, outlined in orange, is the new stop.

The menu at D is unchanged: still `a1, a2`. Every per-pair success rate is
unchanged. Only the destination column of the log differs.

---

## 2. The six interventions

```mermaid
flowchart TD
  T(["Target link T*<br/>on the optimal route"])
  U(["Off-route link U*"])
  N(["No edit"])

  T ==> RD(["redirect<br/>p kept, destination moves"])
  T ==> SB(["silent_break<br/>p to 0, stays on the menu"])
  T ==> HR(["hard_removal<br/>leaves the menu"])
  T ==> DG(["degradation<br/>p halved, stochastic only"])
  U -.-> IR(["irrelevant<br/>p to 0, off every best route"])
  N -.-> NC(["no_change"])

  classDef anchor fill:#E8590C,stroke:#9A3412,stroke-width:3px,color:#FFFFFF
  classDef hot fill:#FFE8D6,stroke:#E8590C,stroke-width:2.5px,color:#7A2E0E
  classDef star fill:#FFFFFF,stroke:#9A3412,stroke-width:3.5px,color:#9A3412
  classDef off fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#6B7280
  class T anchor
  class SB,HR,DG hot
  class RD star
  class U,N,IR,NC off
  linkStyle 0 stroke:#9A3412,stroke-width:5px
  linkStyle 1,2,3 stroke:#E8590C,stroke-width:2.5px
  linkStyle 4,5 stroke:#D1D5DB,stroke-width:1.5px
```

All four route-changing conditions share one target stream, so for a given
seed they edit the same T\*. `redirect` is drawn heaviest: it is the only one
a counting method cannot solve. The two controls are grey.

---

## 3. Two-turn probe delivery

```mermaid
flowchart LR
  A(["Turn 1<br/>Period A only"]) ==> A2(["belief_pre"])
  A --> A1(["route_pre"])
  A2 ==> B(["Turn 2<br/>Period B revealed<br/>turn 1 still in context"])
  A1 --> B
  B --> B1(["detection"])
  B --> B2(["localization"])
  B --> B3(["preservation"])
  B --> B4(["adaptation"])
  B ==> B5(["belief_post"])
  B5 ==> SC(["self-consistency<br/>preservation"])
  A2 -.-> SC

  classDef stage fill:#FFE8D6,stroke:#E8590C,stroke-width:2.5px,color:#7A2E0E
  classDef star fill:#E8590C,stroke:#9A3412,stroke-width:3px,color:#FFFFFF
  classDef plain fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#6B7280
  class A,B,A2,B5 stage
  class SC star
  class A1,B1,B2,B3,B4 plain
  linkStyle 0,2,8,9 stroke:#E8590C,stroke-width:3px
  linkStyle 10 stroke:#9A3412,stroke-width:2.5px,stroke-dasharray:5 3
  linkStyle 1,3,4,5,6,7 stroke:#D1D5DB,stroke-width:1px
```

The orange path is the belief chain: elicit beliefs on Period A, reveal
Period B, re-elicit, then score the second set against the model's own first
set rather than against ground truth. It is the only probe measuring
self-consistency rather than correctness. The grey probes are scored against
ground truth.

---

## 4. The null model and the three regions

```mermaid
flowchart TD
  EV(["Same prompt view<br/>same rendering, same K"])
  EV --> BL(["Evidence-only baseline<br/>counts success rates,<br/>names the largest swing"])
  EV --> MD(["Model"])
  BL --> CMP{"Model vs baseline<br/>on the same instances"}
  MD --> CMP
  CMP -.->|"above, redirect only,<br/>not yet run"| AB(["Extracted something<br/>counting cannot reach"])
  CMP -->|"at"| AT(["Behaving as a counter"])
  CMP ==>|"below, where we are"| BE(["Had the information,<br/>did not use it<br/><br/>silent_break 0.26 vs 0.96<br/>irrelevant 0.39 vs 1.00"])

  classDef plain fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#374151
  classDef open fill:#FFFFFF,stroke:#9A3412,stroke-width:3px,stroke-dasharray:5 3,color:#9A3412
  classDef star fill:#E8590C,stroke:#9A3412,stroke-width:3.5px,color:#FFFFFF
  class EV,BL,MD,AT plain
  class AB open
  class BE star
  linkStyle 4 stroke:#9A3412,stroke-width:2px,stroke-dasharray:5 3
  linkStyle 6 stroke:#9A3412,stroke-width:6px
  linkStyle 0,1,2,3,5 stroke:#D1D5DB,stroke-width:1.5px
```

Measured on 23 matched seeds at K = 10, stochastic. The dashed outline is the
region `redirect` was built to open; it stays dashed until a model has been
run there.

---

## 5. Why redirect defeats the counter

```mermaid
flowchart LR
  Q{"What changed<br/>between the periods?"}
  Q --> R1(["per-pair success rates<br/>0.62 and 0.62<br/>no signal"])
  Q --> R2(["action menu at D<br/>a1, a2 and a1, a2<br/>no signal"])
  Q ==> R3(["where attempts land<br/>B becomes H<br/>the only trace"])

  classDef ask fill:#FFE8D6,stroke:#E8590C,stroke-width:2.5px,color:#7A2E0E
  classDef dead fill:#F3F4F6,stroke:#D1D5DB,stroke-width:1px,color:#9CA3AF
  classDef star fill:#E8590C,stroke:#9A3412,stroke-width:3.5px,color:#FFFFFF
  class Q ask
  class R1,R2 dead
  class R3 star
  linkStyle 0,1 stroke:#D1D5DB,stroke-width:1.5px
  linkStyle 2 stroke:#9A3412,stroke-width:6px
```

Two of the three columns a counting method reads are identical across
periods. Only the third carries the change, and a rate comparison never looks
there. In deterministic mode this is absolute: every link is p = 1, so all
fifteen pairs tie at exactly zero and the counter has nothing.

Baseline localization on `redirect`: 0.09 at K = 5, 0.00 at K = 10, 0.04 at
K = 20. Flat, because more evidence cannot create a signal that is not in the
rates.

---

## Figure 2, updated

Orange marks the off-diagonal.

| | Route optimal | Route suboptimal |
| --- | --- | --- |
| **Localization correct** | 3 | 3 |
| **Localization incorrect** | **6** | 11 |

GPT-4o, two-turn, `silent_break`, stochastic, 23 matched seeds, K = 10.
Off-diagonal 9 of 23.

In the lower-left cell the model routed optimally without localizing. Under
two-turn it had already committed to a Period A route before Period B was
revealed, so planning from Period B does not explain those six.

When rendering, fill that cell solid `#E8590C` with white text and give the
upper-right cell the `#FFE8D6` tint with an orange border.

Keep the Gemma figure beside it. Model, K and delivery all changed, so it is
a second row rather than a replacement.

---

## Palette

| use | colour | where |
| --- | --- | --- |
| the finding, the intervention | `#E8590C` solid fill, white text | T\*, `redirect`, below-baseline, the 2x2 cell |
| the heaviest stroke | `#9A3412` | T\* edge, the one arrow that matters |
| on the causal chain | `#FFE8D6` fill, `#E8590C` border | optimal route, belief chain |
| open question, not yet run | white fill, `#9A3412` dashed border | the "above baseline" region |
| off the chain | `#F3F4F6` fill, `#D1D5DB` border | controls, off-route links, ground-truth probes |
| chain text | `#7A2E0E` | labels inside tinted nodes |

Orange is reserved for the intervention and its consequences. Grey is for
everything else.

**One deliberate exception to the no-em-dash rule.** The labels `E — start`
and `F — goal` keep the dash because the existing Figure 1 uses that form.
Matching a published figure beats a prose rule about sentences.
