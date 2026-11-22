# Carbium Scoop bucket

The `carbium` command line for Windows, as one binary without Node.

```pwsh
scoop bucket add carbium https://github.com/carbium-sh/scoop-bucket
scoop install carbium/carbium
carbium --help
```

`scoop update carbium` gets new releases. The binary is the `carbium-windows-x64.exe` or `carbium-windows-arm64.exe`
asset of a `cli-v` release of [carbium-js](https://github.com/carbium-sh/carbium-js/releases), checked against that
release's `SHA256SUMS`. Carbon Stream commands are not in this binary: they need the npm package with
`@triton-one/yellowstone-grpc` on Linux x64 or macOS. `carbium ws tail` works here. Docs:
[packages/cli](https://github.com/carbium-sh/carbium-js/tree/main/packages/cli).

The Excavator workflow moves `bucket/carbium.json` to the release npm calls latest for `carbium`, which moves only after
a CLI release passes the release checks in carbium-js, and `scripts/check-manifest.py` checks it in CI and after every
Excavator run. GitHub turns a schedule off after 60 days without a commit, so after each CLI release run
`gh workflow enable excavator.yml -R carbium-sh/scoop-bucket && gh workflow run excavator.yml -R carbium-sh/scoop-bucket`.

MIT licence.
