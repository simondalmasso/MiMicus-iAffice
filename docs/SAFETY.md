# Safety

ORDER-001 permits reads only. `safety.py` rejects write-like commands and paths, including topic creation/funding, registration/removal, worker/reputer payload insertion, stake/delegation, transaction broadcast, and `Msg*` operations with:

`LIVE_EXECUTION_PROHIBITED_BY_ORDER_001`

The codebase contains no signer interface and no wallet/key loading. HTTP uses HTTPS GET only. Consumer API credentials are not requested or used.

Secret scanning detects credential values such as private-key PEM blocks, bearer tokens, assigned secret/key values, seed phrases, and credential-bearing URLs while allowing documentation to mention security concepts. Logs/evidence do not dump environment variables.

Tests exercise forbidden write paths, credential-bearing URL rejection, secret detection, and the prohibition on running the shadow model engine for TRADING topics.
