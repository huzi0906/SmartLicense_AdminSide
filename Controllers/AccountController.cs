// Liscence_system
using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using MongoDB.Bson;
using MimeKit;
using MailKit.Net.Smtp;
using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using System.Security.Claims;

namespace SmartLicense_AdminSide.Controllers
{
public class AuthController : Controller
{
         private readonly IMongoCollection<BsonDocument> _adminsCollection;

        public AuthController(IMongoClient mongoClient)
        {
            var database = mongoClient.GetDatabase("Liscence_system"); // Replace with your DB name
            _adminsCollection = database.GetCollection<BsonDocument>("Admins");
        }

        // GET: Display the login page
    public IActionResult Login()
    {
        return View();
    }

    // POST: Handle login form submission
    [HttpPost]
    public async Task<IActionResult> Login(string Username, string Password)
    {
        // Validate input
        if (string.IsNullOrEmpty(Username) || string.IsNullOrEmpty(Password))
        {
            ViewBag.ErrorMessage = "Username and Password are required.";
            return View();
        }

        // Query MongoDB for the admin by email
        var filter = Builders<BsonDocument>.Filter.Eq("Email", Username);
        var admin = await _adminsCollection.Find(filter).FirstOrDefaultAsync();

        if (admin == null)
        {
            ViewBag.ErrorMessage = "Invalid username or password.";
            return View();
        }

        // Retrieve stored password
        var storedPassword = admin.Contains("Password") && admin["Password"].IsString
            ? admin["Password"].AsString
            : null;

        // Verify password
        if (storedPassword != Password)
        {
            ViewBag.ErrorMessage = "Invalid username or password.";
            return View();
        }

        // Check if the account is enabled (optional, adjust as per your schema)
        var isEnabled = admin.Contains("IsEnabled") && admin["IsEnabled"].IsBoolean
            ? admin["IsEnabled"].AsBoolean
            : true;

        if (!isEnabled)
        {
            ViewBag.ErrorMessage = "This account is disabled.";
            return View();
        }

        // Set up authentication cookie
        var claims = new[] { new Claim(ClaimTypes.Name, Username) };
        var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, new ClaimsPrincipal(identity));

        // Redirect to the home page on success
        return RedirectToAction("Index", "Home");
    }

        // GET: Forgot Password page
        [HttpGet]
        public IActionResult ForgotPassword()
        {
            return View();
        }

        // POST: Send OTP (or password, based on your query)`
        [HttpPost]
        public async Task<IActionResult> SendOTP(string Email)
        {
            if (string.IsNullOrEmpty(Email))
            {
                ViewBag.ErrorMessage = "Email is required.";
                return View("ForgotPassword");
            }

            // Check if email exists in Admins collection
            var filter = Builders<BsonDocument>.Filter.Eq("Email", Email);
            var admin = await _adminsCollection.Find(filter).FirstOrDefaultAsync();

            if (admin == null)
            {
                ViewBag.ErrorMessage = "Email not found.";
                return View("ForgotPassword");
            }

            // Generate 6-digit OTP
            var otp = new Random().Next(100000, 999999).ToString();

            // Store OTP in session
            HttpContext.Session.SetString("OTP", otp);
            HttpContext.Session.SetString("ResetEmail", Email);

            // Send OTP via email
            await SendEmailAsync(Email, "Your OTP Code", $"Your OTP code is {otp}");

            return RedirectToAction("EnterOTP");
        }

        // GET: Enter OTP page
        [HttpGet]
        public IActionResult EnterOTP()
        {
            return View();
        }

        // POST: Verify OTP
        [HttpPost]
        public IActionResult VerifyOTP(string OTP)
        {
            var storedOTP = HttpContext.Session.GetString("OTP");
            if (string.IsNullOrEmpty(storedOTP) || storedOTP != OTP)
            {
                ViewBag.ErrorMessage = "Invalid OTP.";
                return View("EnterOTP");
            }

            // OTP is correct, proceed to reset password
            return RedirectToAction("ResetPassword");
        }

        // GET: Resend OTP
        [HttpGet]
        public async Task<IActionResult> ResendOTP()
        {
            var email = HttpContext.Session.GetString("ResetEmail");
            if (string.IsNullOrEmpty(email))
            {
                return RedirectToAction("ForgotPassword");
            }

            // Generate new OTP
            var otp = new Random().Next(100000, 999999).ToString();
            HttpContext.Session.SetString("OTP", otp);

            // Send OTP via email
            await SendEmailAsync(email, "Your OTP Code", $"Your OTP code is {otp}");

            return RedirectToAction("EnterOTP");
        }

        // GET: Reset Password page
        [HttpGet]
        public IActionResult ResetPassword()
        {
            return View();
        }

        // POST: Change Password
        [HttpPost]
        public async Task<IActionResult> ChangePassword(string NewPassword, string ConfirmPassword)
        {
            if (NewPassword != ConfirmPassword)
            {
                ViewBag.ErrorMessage = "Passwords do not match.";
                return View("ResetPassword");
            }

            var email = HttpContext.Session.GetString("ResetEmail");
            if (string.IsNullOrEmpty(email))
            {
                return RedirectToAction("ForgotPassword");
            }

            // Update password in database
            var filter = Builders<BsonDocument>.Filter.Eq("Email", email);
            var update = Builders<BsonDocument>.Update.Set("Password", NewPassword); // Consider hashing in production
            await _adminsCollection.UpdateOneAsync(filter, update);

            // Clear session
            HttpContext.Session.Remove("OTP");
            HttpContext.Session.Remove("ResetEmail");

            return RedirectToAction("Login"); // Adjust to your login action
        }

        // Helper method to send email
        private async Task SendEmailAsync(string toEmail, string subject, string body)
        {
            var email = new MimeMessage();
            email.From.Add(new MailboxAddress("Smart License Admin", "mhuzaifaahmad@gmail.com")); // Replace with your email
            email.To.Add(new MailboxAddress("", toEmail));
            email.Subject = subject;
            email.Body = new TextPart("plain") { Text = body };

            using var smtp = new SmtpClient();
            await smtp.ConnectAsync("smtp.gmail.com", 587, MailKit.Security.SecureSocketOptions.StartTls);
            await smtp.AuthenticateAsync("mhuzaifaahmad@gmail.com", "mgjlhpxbjcgecrns"); // Replace with your credentials
            await smtp.SendAsync(email);
            await smtp.DisconnectAsync(true);
        }

}
}