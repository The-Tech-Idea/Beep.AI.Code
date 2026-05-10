using System.Text.Json;
using Microsoft.Build.Locator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.MSBuild;

// Register MSBuild
if (!MSBuildLocator.IsRegistered)
{
    MSBuildLocator.RegisterDefaults();
}

var argsList = args.ToList();
var command = "analyze";
var solutionPath = "";
var projectPath = "";

for (int i = 0; i < argsList.Count; i++)
{
    switch (argsList[i])
    {
        case "--solution":
        case "-s":
            solutionPath = i + 1 < argsList.Count ? argsList[++i] : "";
            break;
        case "--project":
        case "-p":
            projectPath = i + 1 < argsList.Count ? argsList[++i] : "";
            break;
        case "--command":
        case "-c":
            command = i + 1 < argsList.Count ? argsList[++i] : "symbols";
            break;
    }
}

if (string.IsNullOrEmpty(solutionPath) && string.IsNullOrEmpty(projectPath))
{
    Console.Error.WriteLine("Error: --solution or --project is required.");
    Environment.Exit(1);
}

try
{
    object result = command switch
    {
        "symbols" => await AnalyzeSymbols(solutionPath, projectPath),
        "diagnostics" => await AnalyzeDiagnostics(solutionPath, projectPath),
        "dependencies" => await AnalyzeDependencies(solutionPath, projectPath),
        _ => await AnalyzeSymbols(solutionPath, projectPath)
    };

    var options = new JsonSerializerOptions { WriteIndented = true };
    Console.WriteLine(JsonSerializer.Serialize(result, options));
}
catch (Exception ex)
{
    Console.Error.WriteLine($"Error: {ex.Message}");
    Environment.Exit(1);
}

static async Task<object> AnalyzeSymbols(string solutionPath, string projectPath)
{
    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (s, e) => Console.Error.WriteLine($"Workspace failed: {e.Diagnostic.Message}");

    Solution? solution = null;
    if (!string.IsNullOrEmpty(solutionPath))
    {
        solution = await workspace.OpenSolutionAsync(solutionPath);
    }
    else if (!string.IsNullOrEmpty(projectPath))
    {
        var proj = await workspace.OpenProjectAsync(projectPath);
        solution = proj.Solution;
    }

    if (solution == null)
    {
        return new { ok = false, error = "Failed to load solution or project." };
    }

    var projects = new List<object>();
    foreach (var project in solution.Projects)
    {
        var projectInfo = new
        {
            name = project.Name,
            filePath = project.FilePath ?? "",
            documents = await GetDocumentSymbols(project)
        };
        projects.Add(projectInfo);
    }

    return new { ok = true, projects };
}

static async Task<List<object>> GetDocumentSymbols(Project project)
{
    var docs = new List<object>();
    foreach (var document in project.Documents)
    {
        var syntaxRoot = await document.GetSyntaxRootAsync();
        if (syntaxRoot is null) continue;

        var symbols = new List<object>();
        foreach (var node in syntaxRoot.DescendantNodes())
        {
            switch (node)
            {
                case ClassDeclarationSyntax cls:
                    symbols.Add(new
                    {
                        kind = "class",
                        name = cls.Identifier.Text,
                        namespaceName = GetNamespace(cls),
                        line = cls.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
                        methods = cls.Members.OfType<MethodDeclarationSyntax>()
                            .Select(m => m.Identifier.Text).ToList(),
                        properties = cls.Members.OfType<PropertyDeclarationSyntax>()
                            .Select(p => p.Identifier.Text).ToList()
                    });
                    break;
                case InterfaceDeclarationSyntax iface:
                    symbols.Add(new
                    {
                        kind = "interface",
                        name = iface.Identifier.Text,
                        namespaceName = GetNamespace(iface),
                        line = iface.GetLocation().GetLineSpan().StartLinePosition.Line + 1
                    });
                    break;
                case StructDeclarationSyntax st:
                    symbols.Add(new
                    {
                        kind = "struct",
                        name = st.Identifier.Text,
                        namespaceName = GetNamespace(st),
                        line = st.GetLocation().GetLineSpan().StartLinePosition.Line + 1
                    });
                    break;
                case EnumDeclarationSyntax en:
                    symbols.Add(new
                    {
                        kind = "enum",
                        name = en.Identifier.Text,
                        namespaceName = GetNamespace(en),
                        line = en.GetLocation().GetLineSpan().StartLinePosition.Line + 1
                    });
                    break;
                case RecordDeclarationSyntax rec:
                    symbols.Add(new
                    {
                        kind = "record",
                        name = rec.Identifier.Text,
                        namespaceName = GetNamespace(rec),
                        line = rec.GetLocation().GetLineSpan().StartLinePosition.Line + 1
                    });
                    break;
            }
        }

        if (symbols.Count > 0)
        {
            docs.Add(new
            {
                name = document.Name,
                filePath = document.FilePath ?? "",
                symbols
            });
        }
    }
    return docs;
}

static async Task<object> AnalyzeDiagnostics(string solutionPath, string projectPath)
{
    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (s, e) => Console.Error.WriteLine($"Workspace failed: {e.Diagnostic.Message}");

    Solution? solution = null;
    if (!string.IsNullOrEmpty(solutionPath))
    {
        solution = await workspace.OpenSolutionAsync(solutionPath);
    }
    else if (!string.IsNullOrEmpty(projectPath))
    {
        var proj = await workspace.OpenProjectAsync(projectPath);
        solution = proj.Solution;
    }

    if (solution == null)
    {
        return new { ok = false, error = "Failed to load solution or project." };
    }

    var diagnostics = new List<object>();
    foreach (var project in solution.Projects)
    {
        var compilation = await project.GetCompilationAsync();
        if (compilation == null) continue;

        foreach (var diag in compilation.GetDiagnostics())
        {
            if (diag.Severity == DiagnosticSeverity.Error || diag.Severity == DiagnosticSeverity.Warning)
            {
                var lineSpan = diag.Location.GetLineSpan();
                diagnostics.Add(new
                {
                    file = lineSpan.Path,
                    line = lineSpan.StartLinePosition.Line + 1,
                    column = lineSpan.StartLinePosition.Character + 1,
                    severity = diag.Severity.ToString().ToLower(),
                    code = diag.Id,
                    message = diag.GetMessage()
                });
            }
        }
    }

    return new { ok = true, diagnostics };
}

static async Task<object> AnalyzeDependencies(string solutionPath, string projectPath)
{
    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (s, e) => Console.Error.WriteLine($"Workspace failed: {e.Diagnostic.Message}");

    Solution? solution = null;
    if (!string.IsNullOrEmpty(solutionPath))
    {
        solution = await workspace.OpenSolutionAsync(solutionPath);
    }
    else if (!string.IsNullOrEmpty(projectPath))
    {
        var proj = await workspace.OpenProjectAsync(projectPath);
        solution = proj.Solution;
    }

    if (solution == null)
    {
        return new { ok = false, error = "Failed to load solution or project." };
    }

    var deps = new List<object>();
    foreach (var project in solution.Projects)
    {
        var projectDeps = new List<string>();
        foreach (var refProj in project.ProjectReferences)
        {
            var refProject = solution.GetProject(refProj.ProjectId);
            if (refProject != null)
            {
                projectDeps.Add(refProject.Name);
            }
        }
        deps.Add(new
        {
            name = project.Name,
            dependencies = projectDeps
        });
    }

    return new { ok = true, dependencies = deps };
}

static string GetNamespace(BaseTypeDeclarationSyntax typeDecl)
{
    var parent = typeDecl.Parent;
    while (parent != null)
    {
        if (parent is NamespaceDeclarationSyntax ns)
            return ns.Name.ToString();
        if (parent is FileScopedNamespaceDeclarationSyntax fsns)
            return fsns.Name.ToString();
        parent = parent.Parent;
    }
    return "";
}
