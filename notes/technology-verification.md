# Technology choices: items still to verify

`_data/tech.yml` publishes only licences (checked against each repository on 2026-11-11) and capabilities confirmed from documentation. These capabilities were reported but not confirmed in the verification pass, and are deliberately not claimed on the site. Confirm before adding them.

## Gateways
- [ ] LiteLLM: retries, fallbacks, cooldown/circuit breaking, OTel export, per-request cost tracking (docs pages not read)
- [ ] Agent Router (formerly Envoy AI Gateway): token rate limits, currency budgets, OTel
- [ ] Portkey OSS gateway: budgets, rate limits, circuit breaker in OSS vs enterprise; 2.0 merges enterprise features (pre-release)
- [ ] agentgateway: which features are only in the vendor's enterprise distribution
- [ ] Any gateway that pins or detects changes to MCP tool descriptions (none found)

## Policy
- [ ] OPA decision logging and conftest details; Cedar/Cerbos test tooling (licences confirmed; features from memory)

## Durable execution and release
- [ ] Temporal: activity result recording, durable timers, signals, workflow-ID dedup, Worker Versioning (core concepts; pages not read in this pass)
- [ ] DBOS: version pinning across deploys
- [ ] Argo Rollouts / Flagger: metric-based rollback, traffic mirroring (pages loaded, not read)
- [ ] Unleash: licence (repository reports AGPL-3.0) — confirm with legal before listing as an alternative

## Identity, egress, privacy
- [ ] Cilium toFQDNs and L7 policies; Istio egress gateway; Squid ACLs
- [ ] SPIRE federation to cloud providers
- [ ] OpenBao transit for per-tenant keys and key destruction
- [ ] Presidio encrypt/decrypt (reversible) operators

## Observability, evaluation, data
- [ ] promptfoo, Inspect, DeepEval: trajectory evaluation, dataset versioning, CI specifics
- [ ] GrowthBook: whether holdouts are in the MIT core or the enterprise directories
- [ ] Qdrant / Phoenix RBAC in OSS editions
- [ ] OpenMetadata / DataHub deletion workflows; mem0 provenance metadata
