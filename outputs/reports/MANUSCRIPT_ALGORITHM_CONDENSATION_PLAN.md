# Manuscript Algorithm Condensation Plan

## Executive Summary

The manuscript algorithm section can be shortened without changing the
scientific chain by making the three stages explicit and moving implementation
specifics to numerical-method notes. The safest structure is:

1. Stage 1: DL-only coarse localization.
2. Stage 2: joint spatial LM over positions/clocks.
3. Stage 3: dynamic soft-information refinement using prior covariance and new
   measurements.
4. Numerical implementation notes: residual-scaled covariance, clock-drift
   state, non-truth observability/safeguard, and single-UE baseline semantics,
   only if C7 becomes the chosen final algorithm.

No manuscript edits were made.

## Condensed Outline

### Stage 1: DL-Only Coarse Localization

Keep the WNLS/GN equations. Condense prose to state:

- each UE uses only its own satellite DL measurements from the first interval;
- clock terms are fixed to zero for this baseline/initialization;
- the output is a per-UE position estimate packed into the initial theta.

Suggested safe language:

> The first stage provides a DL-only initialization. Each UE solves a
> precision-weighted GN problem using its own satellite downlink measurements,
> with clock states fixed to zero, and the resulting positions initialize the
> cooperative estimator.

### Stage 2: Joint Spatial LM Over Positions/Clocks

Keep the LM/WNLS objective and Hessian expression. Add only one short sentence
if final code defensibility needs it:

> In the numerical implementation, LM candidate steps are accepted using
> observable residual-cost and trust-region checks, not truth-state error.

Avoid expanding the main theory section with migration-ladder detail.

### Stage 3: Dynamic Soft-Information Refinement

Condense lines 1386-1388. The current text spends too much space comparing the
formulation to EM, Viterbi, Kalman filtering, and EKF. A shorter version should
say the stage is a Bayesian information update over the joint position/clock
state and then move quickly to `x`, `Pi`, `F`, `Q`, `P`, and the Gaussian
linearized update.

Suggested safe language:

> The final stage recursively fuses soft context information from the dynamic
> state model with soft feature information from the DL/SL measurements. This
> yields a Bayesian prediction/update formulation over the network state; under
> a Gaussian prior and a first-order measurement linearization, the update takes
> the information-form expression below.

### Numerical Implementation Notes

Add this only after a human chooses C7 as the final algorithm:

> For the C7 candidate implementation used in the code-provenance path, the
> refinement state augments the gauged position/clock vector with non-reference
> clock-drift components. The initial refinement covariance is estimated from
> residual-scaled LM curvature, then typed blocks are extracted and diagonal
> clipped. A non-truth safeguard reverts weakly observable clock/drift updates,
> including single-UE clock updates, while preserving position updates.

This should appear as a numerical-method note, not as a replacement for the
general SCI/SFI derivation, unless the final manuscript deliberately switches
to a C7-specific derivation.

## Must Preserve

- The three-stage architecture.
- The gauged parameter vector with the first satellite as reference.
- The distinction between `theta` and `x`.
- The projection relationship `theta=Pi x`.
- The distinction between clock offset and clock drift.
- DL/SL measurement semantics.
- The fact that single-UE cases cannot exploit cooperation.
- The distinction between theoretical framework and non-final diagnostic code.

## Safe Wording

- "DL-only coarse localization baseline."
- "Cooperative weighted LM over the gauged joint position/clock vector."
- "Bayesian information-form refinement under a Gaussian prior and linearized
  measurement likelihood."
- "C7 candidate implementation."
- "typed block-extracted, diagonal-clipped residual-scaled covariance."
- "non-truth synchronization safeguard."
- "single-UE clock/drift update is not observable in this safeguard."
- "non-final diagnostic output."

## Unsafe Wording

- "C7 is manuscript-ready."
- "Current C7 figures validate final refined-JCLS results."
- "Generic EKF/MAP refinement was used for all reported figures" unless the
  final code path confirms this.
- "Single-UE refined JCLS improves synchronization."
- "Clock drift is estimated by the static offset-only numerical model."
- "Full block covariance" or "cross-covariance" for C7.

## Prioritized Manuscript Actions

### Must Fix Before Submission

1. Decide final Step 3 implementation for figures and align the numerical
   specialization text accordingly.
2. If C7 is final, revise the numerical-method text to mention clock drift,
   residual-scaled covariance, diagonal clipping, and safeguards.
3. If the identity-state SCI/SFI helper is final instead, do not cite C7
   candidate behavior as manuscript evidence.
4. Clarify that `N_u=1` is no-cooperation/baseline semantics, not cooperative
   JCLS synchronization improvement.
5. Define synchronization error relative to the reference satellite and
   excluding the reference clock.

### Should Fix If Time

- Shorten the soft-information prose before the `x`, `Pi`, `F`, `Q`, `P`
  equations.
- Replace broad EM/Viterbi/Kalman discussion with one compatibility sentence.
- Make Step 1 "DL-only" explicit in prose and figure captions where relevant.
- Add a brief note on internal range-equivalent clock units if implementation
  details are discussed.

### Nice To Have

- Add a compact numerical-method paragraph after the algorithm equations rather
  than scattering implementation caveats through the theory text.
- Keep C7 provenance labels out of the main manuscript unless they are needed
  for auditability.
- Leave the commented Jacobian appendix inactive unless it is fully checked
  against current sign conventions.

## Proposed Minimal Edit Strategy

Risk classification: high if final results or Step 3 state/covariance claims
are changed; medium if only clarifying single-UE semantics and shortening
generic prose.

1. Plan the edit against the chosen final code path.
2. Touch only the algorithm and numerical-results bridge paragraphs.
3. Do not alter equations unless the final code path requires it.
4. Compile after the manuscript edit.
5. Audit claims against the final approved report/figure provenance.

## Recommended Next Action

Hold manuscript edits until a human chooses whether the final algorithm path is
generic identity-state SCI/SFI or C7. Then produce a surgical edit plan with
exact replacement passages and no figure/result changes.
