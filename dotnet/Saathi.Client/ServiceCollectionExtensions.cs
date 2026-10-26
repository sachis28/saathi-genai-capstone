using Microsoft.Extensions.DependencyInjection;

namespace Saathi.Client;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddSaathiClient(this IServiceCollection services, string mode, string baseUrl)
    {
        var clientMode = Enum.Parse<ClientMode>(mode, ignoreCase: true);

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