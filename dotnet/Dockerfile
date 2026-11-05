# Saathi Blazor UI. Build with the dotnet/ folder as context: az acr build -t saathi-web dotnet
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish Saathi.Web/Saathi.Web.csproj -c Release -o /out

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /out .
# Container Apps terminates TLS; the app listens on plain HTTP inside the container.
ENV ASPNETCORE_URLS=http://+:8080 Saathi__Mode=Http
EXPOSE 8080
ENTRYPOINT ["dotnet", "Saathi.Web.dll"]
