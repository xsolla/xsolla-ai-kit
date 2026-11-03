# nocode-shop-setup

The entry to the Shop Builder path: a shop the user creates on Xsolla's side without
writing code. It checks what can be built, asks one batch of questions, and hands off to
`description-to-shop` and `shop-builder-assembly` for a store, or `game-web-portal` for a
game home.

## Spec

[references/storefront-by-default.md](references/storefront-by-default.md) is the one spec
for the Shop Builder path: goal, success metrics, requirements R1–R11 with their status,
open decisions, and dependencies on other teams. A pull request that works on the path
updates the spec's Status column in the same pull request.
