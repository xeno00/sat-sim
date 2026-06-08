# Step C5 Sliding-Window MAP Comparison

## Executive Summary

- Grid: `medium`
- C5 status: `major_degradation`
- Improves over C4: `False`
- Approaches Step B or legacy behavior: `False`
- Step 3 defensible now: `False`

## Aggregate Diagnostics

- Localization improvement rows: 8 of 9
- Synchronization improvement rows: 7 of 9
- Step-3 accepted/rejected solver steps: 19/35
- Objective components: `['dynamics_objective', 'measurement_objective', 'prior_objective', 'total_objective']`

## Row Comparisons Against Step B

| Nu | Ns | Status vs Step B | Step B pos [m] | C5 pos [m] | Step B sync [s] | C5 sync [s] | Step3 acc/rej | J total decrease |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 4 | `healthy` | 0.26229065223009157 | 0.26229065223009157 | 2.1421024323915456e-10 | 2.1421024323915456e-10 | 0/0 | None |
| 1 | 8 | `healthy` | 0.23928421797729885 | 0.23928421797729885 | 3.740229093377279e-10 | 3.740229093377279e-10 | 0/0 | None |
| 1 | 12 | `healthy` | 0.39234181975549676 | 0.39234181975549676 | 6.288413967376565e-10 | 6.288413967376565e-10 | 0/0 | None |
| 3 | 4 | `mild_degradation` | 0.2131941128459946 | 0.3151576169073507 | 1.3351889972769755e-10 | 1.3893616010752704e-10 | 3/3 | 28.835668095301113 |
| 3 | 8 | `mild_degradation` | 0.05374084598746667 | 0.0965307303895113 | 2.515678196318507e-10 | 7.72910350114867e-11 | 3/3 | 90.37907957018976 |
| 3 | 12 | `major_degradation` | 0.022860981344926663 | 0.06430749876719007 | 7.447557176800584e-11 | 6.255069004539848e-11 | 1/5 | 76.8989714254956 |
| 5 | 4 | `mild_degradation` | 0.1700512820767665 | 0.17925013080181434 | 1.4494523083046297e-10 | 2.428967193651001e-10 | 2/4 | 90.41143056066048 |
| 5 | 8 | `major_degradation` | 0.04523821719692235 | 0.021703851419712775 | 7.754213241242157e-11 | 2.2554635483154607e-10 | 1/5 | 127.5906527636665 |
| 5 | 12 | `mild_degradation` | 0.023888533003920628 | 0.007960414006900689 | 5.109866734455777e-11 | 9.893295852838404e-11 | 1/5 | 125.43796570665486 |
| 7 | 4 | `major_degradation` | 0.05961863505009501 | 0.036803539798125014 | 7.160304341120762e-11 | 2.4366653995397013e-10 | 4/2 | 117.78400020884294 |
| 7 | 8 | `major_degradation` | 0.0051434377395518606 | 0.013092159783767533 | 9.337374203473802e-11 | 5.4589411687972505e-11 | 1/5 | 120.66717760751868 |
| 7 | 12 | `major_degradation` | 0.0031973234619046484 | 0.010620218513787916 | 1.321066583145034e-10 | 7.38054412624939e-11 | 3/3 | 188.46348942430132 |
