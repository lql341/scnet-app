# Runtime prerequisites

English | [中文](prerequisites_CN.md)

Use this reference with `contract.md` when preparing an application for a
specific SCNet deployment. List the exact modules, their roles, loading order,
conflicts, backend/runtime requirements and the observed failure mode for a
missing prerequisite.

Keep the six-axis stack signature in `app.json` and in private evidence. The
platform axis identifies where the result was obtained; the backend version and
product target identify the binary compatibility label.

Runtime and ABI dependencies supplied by the cluster belong here. Bundle only
redistributable application-specific libraries, with their license, version,
checksum and size recorded in the package review.
