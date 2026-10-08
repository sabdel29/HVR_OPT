# What we need from the system owner

Eight questions. Everything else is ours.

The reliability model is finished to the point where it gives a **validated relative answer**:
the backside architecture (Z2) outlives the embedded one (Z1) by **21–38 %**, for an electrical
cost of **+1.688 W (1.3 %)**. To turn that into a **pass/fail** we need to know what the product
must survive. We cannot derive that, and we will not assume it.

---

### 1. Intended service lifetime
How many **years** must the package survive in the field?

### 2. Survival target
What fraction of the population must survive that lifetime, and to what confidence?
*(e.g. "99 % at 90 % confidence". This matters because the model predicts **mean** life, and
converting to a population fraction needs the target stated.)*

### 3. Cold boots / full shutdowns
How many times per day (or per week, or per year) does the system go from fully **off and at
ambient** to **full operating temperature**?
*This is the single most damaging cycle type and usually dominates the answer.*

### 4. Large workload thermal cycles
Beyond cold boots, how many **deep power swings** per day does a typical part see — idle-to-full
or similar? Roughly how large, in °C at the die or in % of full power?

### 5. Typical high-power dwell
When the part is at high power, how long does it stay there — seconds, minutes, hours?
*A rough figure is fine: we measured this to change the answer by only 17–22 % across a 30×
range.*

### 6. Is the system ever fully powered down?
Yes / no. **If it is never fully powered down, the temperature swing is far smaller than we have
assumed and solder fatigue may not be life-limiting at all.**

### 7. Is the requirement a field mission or a qualification gate?
Which of these is the number in question 1?
* **A — field mission**: what the product must actually survive in service;
* **B — product design requirement**: an internal target your organisation has set;
* **C — qualification test**: an accelerated test such as JEDEC −40/+125 °C, 1000 cycles.

*These are not interchangeable and we will not convert one into another without being told to.
If the answer is C, please say whether you want it **adopted** as the design target.*

### 8. Existing internal package-reliability target
Does your organisation already have a solder-joint or package reliability specification for
this class of product? If so, we would rather use it than construct one.

---

## What we are **not** asking you for

Material properties, fatigue exponents, mesh or model parameters, failure criteria, or anything
about the mechanics. Those are ours and they are settled.

## What happens when you answer

| answer | what we can say immediately |
|---|---|
| a required life **below ~474 cycles** | all architectures pass robustly — solder fatigue is **not** a design constraint, and the architecture choice can be made on electrical grounds alone |
| **474 – 3206 cycles** | **currently undecidable** — our two admitted life-law families disagree over this band. A board-level calibration test (designed, costed and ready in `BOARD_LEVEL_CALIBRATION_PLAN.md`) would resolve it |
| **above ~3206 cycles** | all architectures fail robustly — reliability is limiting and the Z1 → Z2 choice does **not** solve it; a different intervention is needed |

Most plausible datacenter missions we can construct land in the second or third row, which is
why the calibration test is recommended **in parallel** with your answer rather than after it.
