using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using MongoDB.Bson;
using System.Threading.Tasks;

public class AuthController : Controller
{
    private readonly IMongoCollection<BsonDocument> _adminsCollection;

    // Inject IMongoClient via constructor
    public AuthController(IMongoClient mongoClient)
    {
        var database = mongoClient.GetDatabase("Liscence_system");
        _adminsCollection = database.GetCollection<BsonDocument>("Admins");
    }

    // GET: Display the login view
    public IActionResult Login() => View();

    public IActionResult ForgotPassword() => View();

    public IActionResult EnterOTP() => View();

    public IActionResult ResetPassword() => View();

    // POST: Handle login form submission
    [HttpPost]
    public async Task<IActionResult> Login(string Username, string Password)
    {
        // Check if username or password is empty
        if (string.IsNullOrEmpty(Username) || string.IsNullOrEmpty(Password))
        {
            ViewBag.ErrorMessage = "Username and Password are required.";
            return View();
        }

        // Query the Admins collection for a document with matching Email
        var filter = Builders<BsonDocument>.Filter.Eq("Email", Username);
        var admin = await _adminsCollection.Find(filter).FirstOrDefaultAsync();

        // If no admin is found, return an error
        if (admin == null)
        {
            ViewBag.ErrorMessage = "Invalid username or password.";
            return View();
        }

        // Safely retrieve the stored password
        var storedPassword = admin.Contains("Password") && admin["Password"].IsString
            ? admin["Password"].AsString
            : null;

        // Verify the password
        if (storedPassword != Password)
        {
            ViewBag.ErrorMessage = "Invalid username or password.";
            return View();
        }

        // Check if the admin account is enabled
        var isEnabled = admin.Contains("IsEnabled") && admin["IsEnabled"].IsBoolean
            ? admin["IsEnabled"].AsBoolean
            : false;

        if (!isEnabled)
        {
            ViewBag.ErrorMessage = "This account is disabled.";
            return View();
        }

        // Successful login: redirect to Home/Index
        return RedirectToAction("Index", "Home");
    }

    [HttpPost]
    public IActionResult SendOTP(string Email)
    {
        // Send OTP logic (unchanged)
        return RedirectToAction("EnterOTP");
    }

    [HttpPost]
    public IActionResult VerifyOTP(string OTP)
    {
        // Verify OTP logic (unchanged)
        return RedirectToAction("ResetPassword");
    }

    [HttpPost]
    public IActionResult ChangePassword(string NewPassword, string ConfirmPassword)
    {
        // Change password logic (unchanged)
        return RedirectToAction("Login");
    }
}