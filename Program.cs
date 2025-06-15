using DotNetEnv;
using Microsoft.AspNetCore.Authentication.Cookies;
using MongoDB.Driver;
using SmartLicense_AdminSide.Hubs;

Env.Load();

var builder = WebApplication.CreateBuilder(args);

// Load env variables
builder.Configuration.AddEnvironmentVariables();

// Register IMongoClient as a singleton
builder.Services.AddSingleton<IMongoClient>(sp =>
    new MongoClient(builder.Configuration["MONGODB_URI"]));

// Register IMongoDatabase using the configured database name
builder.Services.AddScoped<IMongoDatabase>(sp =>
{
    var client = sp.GetRequiredService<IMongoClient>();
    var dbName = builder.Configuration["MONGODB_DATABASE"];
    return client.GetDatabase(dbName);
});

// Add CORS policy
builder.Services.AddCors(options =>
{
    options.AddPolicy("CorsPolicy",
        builder => builder
            .WithOrigins("http://localhost:3000") // Adjust to match your React app's URL
            .AllowAnyMethod()
            .AllowAnyHeader()
            .AllowCredentials());
});

// Add services to the container
builder.Services.AddControllersWithViews();
builder.Services.AddSignalR(); // Add SignalR services
builder.Services.AddScoped<SmartLicense_AdminSide.Services.ChatService>(); // Add ChatService
builder.Services.AddDistributedMemoryCache();
builder.Services.AddSession(options =>
{
    options.IdleTimeout = TimeSpan.FromMinutes(10); // OTP expires after 10 minutes
    options.Cookie.HttpOnly = true;
    options.Cookie.IsEssential = true;
});

// Register authentication services with cookie authentication
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(CookieAuthenticationDefaults.AuthenticationScheme, options =>
    {
        options.LoginPath = "/Auth/Login"; // Redirect to login page if unauthenticated
    });
    
var app = builder.Build();

// Configure the HTTP request pipeline
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseCors("CorsPolicy"); // Apply CORS before routing
app.UseAuthentication(); // Must be before UseAuthorization
app.UseSession();
app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

// Map SignalR hub
app.MapHub<ChatHub>("/chathub");

app.Run();