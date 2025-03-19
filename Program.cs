using DotNetEnv;
using Microsoft.AspNetCore.Authentication.Cookies;
using MongoDB.Driver;

Env.Load();

var builder = WebApplication.CreateBuilder(args);

// Load env variables
builder.Configuration.AddEnvironmentVariables();

// Register IMongoClient as a singleton
builder.Services.AddSingleton<IMongoClient>(sp =>
    new MongoClient(builder.Configuration["MONGODB_URI"]));

// Add services to the container
builder.Services.AddControllersWithViews();
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
app.UseAuthentication(); // Must be before UseAuthorization
app.UseSession();
app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
