# Entry cost

Deployed v0.16.0 code shows `Register` for either a worker or reputer charges the chain `RegistrationFee` through effective-revenue handling before inserting the participant. `CheckBalanceForRegistration` requires the sending account balance to cover that fee. The registration handler itself does **not** impose the reputer stake requirement on a worker.

Live mainnet params observed under emissions v9 report `required_minimum_stake=1000000000000000000`. In deployed v0.16.0 code the **reputer payload** path explicitly checks that minimum stake, while the **worker payload** path checks permission/registration/window and charges `DataSendingFee` without that stake check. Therefore the reputer minimum is not assigned to a worker. The exact live `registration_fee` and `data_sending_fee` values were not safely exposed by the read extraction used for this checkpoint and remain `UNKNOWN`; source-code defaults are not substituted for live state.

Allora's current gas documentation describes transaction gas as wallet-paid and recommends a network gas-price structure. ORDER-001 performs no transaction simulation, so a real worker's gas/min-balance USD cost remains `UNKNOWN`.

Forge Identity is separate from direct chain participation. Official July 22, 2026 material describes watch/link/managed-worker paths; the managed route uses a Forge account/API key and Forge-managed wallet with sponsored eligible network fees under fair-use limits, while registration or other transaction amounts may have separate funding rules. ORDER-001 does not sign up, create an account/API key, accept custody, or use sponsored transactions. Thus `FORGE_REQUIRED=NO_EVIDENCE`, `FORGE_OPTIONAL=YES_FOR_MANAGED_OPERATION`, and `FORGE_USED=NO`.
