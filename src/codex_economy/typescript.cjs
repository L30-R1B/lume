// Official TypeScript compiler API: actual module resolution, aliases and references.
const ts = require(process.argv[2]);
const path = require('node:path');
const root = path.resolve(process.argv[3]);
const config = ts.findConfigFile(root, ts.sys.fileExists);
let options = {allowJs: true, checkJs: true, noEmit: true};
let files;
if (config) {
  const loaded = ts.readConfigFile(config, ts.sys.readFile);
  if (loaded.error) throw new Error(ts.flattenDiagnosticMessageText(loaded.error.messageText, '\n'));
  const parsed = ts.parseJsonConfigFileContent(loaded.config, ts.sys, path.dirname(config));
  options = {...parsed.options, noEmit: true};
  files = parsed.fileNames;
} else {
  files = ts.sys.readDirectory(root, ['.ts','.tsx','.js','.jsx'], ['node_modules','build','dist','.next']);
}
const program = ts.createProgram(files, options);
const checker = program.getTypeChecker();
const facts = [];
for (const source of program.getSourceFiles()) {
  if (source.isDeclarationFile || !path.resolve(source.fileName).startsWith(root + path.sep)) continue;
  function visit(node) {
    if (ts.isIdentifier(node)) {
      let symbol = checker.getSymbolAtLocation(node);
      if (symbol) {
        if (symbol.flags & ts.SymbolFlags.Alias) symbol = checker.getAliasedSymbol(symbol);
        for (const declaration of symbol.declarations || []) {
          const target = declaration.getSourceFile();
          if (!path.resolve(target.fileName).startsWith(root + path.sep)) continue;
          facts.push({source:path.relative(root, source.fileName), line:source.getLineAndCharacterOfPosition(node.getStart()).line+1, name:node.text, target:path.relative(root,target.fileName), target_line:target.getLineAndCharacterOfPosition(declaration.getStart()).line+1, kind:'compiler_reference', status:'resolved_by_tool', origin:'typescript-'+ts.version});
        }
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}
const diagnostics=ts.getPreEmitDiagnostics(program).slice(0,100).map(d => ({code:d.code,message:ts.flattenDiagnosticMessageText(d.messageText,'\n'),file:d.file&&path.relative(root,d.file.fileName)}));
console.log(JSON.stringify({version:ts.version,facts,diagnostics,complete:diagnostics.length===0}));
