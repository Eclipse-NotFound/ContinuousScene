// Diagnostic-only host, never a production deployment artifact.
// The original byCell receiver remains on the operand stack in both branches.
if (state._csUseEnvironmentKeyCacheV1 === true) {
    // Exact cached key bytecode from F15; no changes to its allocation strategy.
    // See ../camera-environment-keycache-20261027/source-equivalent.as.inc.
} else {
    // Exact original A796 key-expression bytecode, offsets [66,117).
    // key = (land.minLocX + int(Math.max(0,x)/1920)) + ":"
    //     + (land.minLocY + int(Math.max(0,y)/1000));
}
// Both paths continue through the identical original live byCell lookup/tail.
