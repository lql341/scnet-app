# Runtime prerequisites

English | [中文](prerequisites_CN.md)

Complete this file before declaring the application deployable. List the exact
module names, their roles, the selected six-axis stack signature, loading order,
conflicts and the observed failure mode when a prerequisite is missing.

The application must not silently switch backend, MPI or CPU/GPU mode. Runtime
and ABI dependencies that are supplied by the cluster belong here; only
redistributable application-specific libraries should be bundled in the runtime
package.

## Selected stack

The generated scaffold has an unconfigured stack in `app.json`. Replace it with
the measured system, toolchain, backend, MPI, framework and platform values
before running a compute job. Keep the complete signature in the private
evidence record and update the compatibility matrix entry after validation.
