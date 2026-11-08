// Startup for the Blazor web app (the agent's workspace UI).
using Saathi.Client;
using Saathi.Web.Components;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Blazor Server: pages run on the server and update the browser over a live connection.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// Register the Saathi client. Mode and API URL come from appsettings.json or environment variables.
builder.Services.AddSaathiClient(
    builder.Configuration["Saathi:Mode"] ?? "Http",
    builder.Configuration["Saathi:ApiUrl"] ?? "http://localhost:8000");

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}
app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
app.UseHttpsRedirection();

// Antiforgery protects forms against cross-site request forgery.
app.UseAntiforgery();

app.MapStaticAssets();
// App.razor is the root component; every page is rendered inside it.
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
