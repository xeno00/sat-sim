# V24 Theory Fix Recommendations

These are exact recommended manuscript edits. Do not apply them without explicit manuscript-edit approval.

## Must Fix Before Resubmission

### 1. Measurement Index and Sign Convention

Add after the scalar measurement model:

```latex
In $h_{i,j}$, node $i$ denotes the transmitting node and node $j$ denotes
the receiving \ac{UE}. Thus the clock term follows the transmitter-minus-
receiver convention in the range-domain model. Equivalently, an implementation
that stores links as receiver--transmitter pairs evaluates the same model as
$\Vert\V{p}_i-\V{p}_j\Vert+c(\delta_i-\delta_j)$ after mapping the stored
transmitter to index $i$ and receiver to index $j$.
```

If the authors intend the opposite physical clock-sign convention, this is not a wording fix; the manuscript equation and code must be reconciled first.

### 2. Mixed LOS/NLOS Row Sets

Replace contiguous row-set definitions:

```latex
\Set{N}_{\mathrm{DL}}=\{1,\dotsc,N_{\mathrm{DL}}\}, \qquad
\Set{N}_{\mathrm{SL}}=\{N_{\mathrm{DL}}+1,\dotsc,N_{\mathrm{DL}}+N_{\mathrm{SL}}\}.
```

with link-type sets that do not assume row contiguity:

```latex
Let $\Set{D}_{\mathrm{DL}}$ and $\Set{D}_{\mathrm{SL}}$ denote the row-index
sets of $\V{h}(\V{\theta})$ and $\RV{z}$ corresponding to \ac{DL} and
\ac{SL} measurements, respectively, with
$|\Set{D}_{\mathrm{DL}}|=N_{\mathrm{DL}}$ and
$|\Set{D}_{\mathrm{SL}}|=N_{\mathrm{SL}}$.
```

Then replace the cases with `i in \Set{D}_{\mathrm{DL}}` and `i in \Set{D}_{\mathrm{SL}}`.

### 3. Fixed Covariance Assumption

Add before the Gaussian LOS FIM:

```latex
For the Fisher-information calculation, the range-domain standard deviations
in $\V{\sigma}$, and hence $\M{R}_{\RV{z}}$, are treated as known quantities
fixed at the operating point. We do not differentiate link variance or
link-availability models with respect to $\V{\theta}$.
```

This blocks the reviewer objection that the Gaussian FIM is missing

```latex
\frac{1}{2}\operatorname{tr}\!\left(
\M{R}_{\RV{z}}^{-1}
\frac{\partial \M{R}_{\RV{z}}}{\partial \theta_a}
\M{R}_{\RV{z}}^{-1}
\frac{\partial \M{R}_{\RV{z}}}{\partial \theta_b}
\right).
```

### 4. CRLB Extraction

Add near the CRLB figure captions or before them:

```latex
Let $\M{C}_{\V{\theta}}$ denote the inverse of the gauged Fisher information
matrix when it is nonsingular. The localization bound plotted for the $i$th
\ac{UE} is the position error bound
$\mathrm{PEB}_i=\sqrt{\operatorname{tr}([\M{C}_{\V{\theta}}]_{\V{p}_i,\V{p}_i})}$,
and the reported average localization bound is
$N_\mathrm{u}^{-1}\sum_{i=1}^{N_\mathrm{u}}\mathrm{PEB}_i$.
Synchronization bounds are computed from the clock-parameter block of the same
gauged covariance matrix, excluding the reference satellite clock
$\delta_{N_\mathrm{u}+1}$, and are converted from seconds to ns for plotting.
```

If satellite clocks are included in the synchronization average, state "UE and non-reference satellite clocks." If only UE clocks are included, state "UE clocks only."

### 5. Rank Condition

Add near the CRLB extraction:

```latex
Finite CRLB curves are reported only when the gauged Fisher information matrix
is nonsingular for the plotted configuration. Rank-deficient cases require an
explicit estimable-subspace or Moore--Penrose-inverse interpretation and are
not reported as ordinary finite CRLBs.
```

## Should Fix

### 6. Covariance Definition

Replace or qualify:

```latex
\M{R}_{\RV{z}}\triangleq \mathbb{C}\mathrm{ov}(\RV{z})=\E{\RV{n}\RV{n}^{\mathrm{T}}}.
```

Safer wording:

```latex
\M{R}_{\RV{z}}\triangleq \mathbb{C}\mathrm{ov}(\RV{z})
=\mathbb{C}\mathrm{ov}(\RV{n}).
```

Then add:

```latex
For the zero-mean Gaussian specialization below, this covariance equals
$\E{\RV{n}\RV{n}^{\mathrm{T}}}$.
```

### 7. NLOS Regularity

Add to the NLOS FIM subsection:

```latex
This score-covariance expression assumes that the range-domain \ac{NLOS}
density is differentiable with finite score covariance, satisfies the usual
regularity condition $\E\{\V{u}\}=\V{0}$, and has support that is independent of
$\V{\theta}$ or whose boundary terms are negligible. When the Gaussian
time-estimation component is convolved with the excess-delay and
multipath-interference components, the resulting full-support density helps
satisfy these conditions.
```

### 8. Directed SL Independence

Add after measurement counts:

```latex
The \ac{SL} count treats reciprocal links as directed measurements. When the
score covariance is taken diagonal, these directed measurement errors are
assumed conditionally independent given the network geometry and link states.
If correlated receiver/transmitter errors are modeled, the full non-diagonal
score covariance $\M{V}$ should be used.
```

### 9. Satellite Positions

Add:

```latex
Satellite ephemeris errors are neglected in this bound; satellite positions
are treated as known inputs rather than estimated components of
$\V{\theta}$.
```

## Nice To Have

- Check whether NR-specific PRS text should cite TS 38.211 in addition to or instead of TS 36.211.
- Move the commented Jacobian appendix to active text or a concise appendix if reviewers need sign/dimension assurance.
- Use `3GPP-relevant` or `3GPP-based` unless every physical-layer detail is directly tied to 3GPP conformance.
