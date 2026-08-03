# J1-R2 One-Time Lockbox Generator Review

## 1. Decision Boundary

This artifact proposes a generator distribution, not exact questions.
Question text, reference answers, labels, and the private source bank remain
outside the repository. The subject Baby model cannot generate, access, or
grade the lockbox.

The generator may be frozen only after explicit user review of the four policy
items below. Exact instances may be generated only after the evaluated model
cutoff is sealed.

## 2. Proposed Sample Plan

| Item | Count |
|---|---:|
| Questions | 24 |
| Positive labels | 24 |
| Explicit negative labels | 72 |
| Fit-pool targets | 8 |
| Development-challenge targets | 8 |
| Lockbox-challenge targets | 8 |
| Minimum private source-bank entries | 48 |
| Minimum entries per target partition | 16 |

Each question has one source-defined positive and three independently
reviewed explicit negatives. Context concepts remain unscored and all other
graph concepts remain unlabeled.

The 24-question size is a balanced implementation diagnostic. It is not a
power analysis and cannot support inferential, broad performance, or
production claims.

## 3. Source And Leakage Rules

- Allowed fact sources are fixed-reference public knowledge and deterministic
  synthetic environments.
- The reviewed source bank is access-controlled and stored outside the repo.
- Personal user memory and live Neo4j relations cannot define truth.
- The subject model cannot see the bank, generate questions, or grade itself.
- The bank must contain at least 48 reviewed entries, including at least 16
  entries for each target partition.
- The bank content hash is fixed before hidden-seed sampling.
- The bank manifest records review method, reviewer or validator identity,
  validator implementation hash when applicable, and a self-hashed review
  provenance record.
- The bank manifest binds the anchor and development question-set hashes and
  requires zero overlap with both.

## 4. Post-Cutoff Generation

1. Freeze the generator distribution before baseline output.
2. Run development-only model selection and seal a model cutoff.
3. Sample the hidden seed after that cutoff.
4. Commit to the seed, cutoff, and private source-bank hash.
5. Sample 8 entries per partition without replacement.
6. Store only the receipt hashes in the repository before opening.
7. Open once, consume once, then release labels only to the next generation.

The seed commitment is:

```text
sha256(utf8(
  "j1-r2-lockbox-v1" + newline +
  seed + newline +
  model_cutoff_sha256 + newline +
  private_source_bank_sha256
))
```

## 5. Review Items

1. Approve a 24-question sample distribution with an `8/8/8`
   target-partition balance, not 24 exact question instances.
2. Approve the external private source-bank and independent-truth policy.
3. Approve post-model-cutoff hidden-seed sampling and commitment.
4. Approve one-time, non-reusable, no-model-selection usage.

The user approved all four items after the distribution wording and
source-bank review-provenance requirements above were added.

## 6. Sealed Contract And Successors

- sample-size plan:
  `3607e14ee99b314a6fb75a957cc4c6e49c17311b08f9662e3e3042997a67b9fb`
- generator implementation:
  `0feb151c93095d54af83700a57248cf2b592d81fb510c2d0e782867b3db360b9`
- generator specification:
  `dde0ffefedd05b7e20f02ac903f55718315eaa403d68f1f78f4c7ba1a18c0898`
- review packet:
  `01bed5589077472f377aa1aa402d83db2e06c785459a3b34137bd0717fb86ffd`
- review decisions:
  `bdd4b58fe362edb734785b73b0e0a00f27fcfdbf4551f69ff024bd2fa3d19fb3`
- generator-frozen manifest:
  `0b5bc0cf40edb8826e1ef4f2cc705c243a02de458f182c93d153ad79a471b46f`
- readiness after freeze:
  `2954f13283c593857e7de70b7352f247438971a9b3e0f8405b59826e659f04f4`

Current successor gates are `review=true`, `generator_freeze=true`, and
`lexical_baseline=true`. Exact question materialization, held-out,
performance, and production gates remain false.
