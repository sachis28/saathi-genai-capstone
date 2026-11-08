using Microsoft.Extensions.DependencyInjection;

namespace Saathi.Client;

// One call (services.AddSaathiClient(...)) registers everything the app needs from this library.
// It also shows the three dependency injection lifetimes: Singleton, Scoped and Transient.
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddSaathiClient(this IServiceCollection services, string mode, string baseUrl)
    {
        // "Mock" or "Http" from configuration -> ClientMode enum.
        var clientMode = Enum.Parse<ClientMode>(mode, ignoreCase: true);

        // A named HttpClient pointing at the API, created and pooled by IHttpClientFactory.
        services.AddHttpClient("saathi", c => c.BaseAddress = new Uri(baseUrl));

        // Singleton: one factory for the whole app
        services.AddSingleton<ICopilotClientFactory>(sp =>
            new CopilotClientFactory(sp.GetRequiredService<IHttpClientFactory>(), clientMode));

        // Scoped: one chat session per scope (per user/request)
        services.AddScoped<ChatSession>();

        // Transient: a new client every time one is asked for
        services.AddTransient<ICopilotClient>(sp =>
            sp.GetRequiredService<ICopilotClientFactory>().Create());

        return services;
    }
}