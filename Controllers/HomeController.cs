using Microsoft.AspNetCore.Mvc;

namespace SmartLicense_AdminPanel.Controllers
{
    public class HomeController : Controller
    {
        public IActionResult Index()
        {
            return View();
        }

        public IActionResult Test()
        {
            return View();
        }

        public IActionResult Feedback()
        {
            return View();
        }

        public IActionResult Logout()
        {
            return RedirectToAction("Index");
        }
    }
}
