using Microsoft.AspNetCore.Mvc;

public class AuthController : Controller
{
    public IActionResult Login() => View();
    public IActionResult ForgotPassword() => View();
    public IActionResult EnterOTP() => View();
    public IActionResult ResetPassword() => View();

    [HttpPost]
    public IActionResult Login(string Username, string Password)
    {
        // Handle login logic
        return RedirectToAction("Index", "Dashboard");
    }

    [HttpPost]
    public IActionResult SendOTP(string Email)
    {
        // Send OTP logic
        return RedirectToAction("EnterOTP");
    }

    [HttpPost]
    public IActionResult VerifyOTP(string OTP)
    {
        // Verify OTP logic
        return RedirectToAction("ResetPassword");
    }

    [HttpPost]
    public IActionResult ChangePassword(string NewPassword, string ConfirmPassword)
    {
        // Change password logic
        return RedirectToAction("Login");
    }
}
