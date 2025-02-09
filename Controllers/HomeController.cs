using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using SmartLicense_AdminSide.Models;

namespace SmartLicense_AdminPanel.Controllers
{
    public class HomeController : Controller
    {
        private readonly IMongoCollection<User> _usersCollection;

        public HomeController(IMongoClient mongoClient)
        {
            var database = mongoClient.GetDatabase("Liscence_system");
            _usersCollection = database.GetCollection<User>("users");
        }

        public async Task<IActionResult> Index()
        {
            var users = await _usersCollection.Find(_ => true).ToListAsync();
            return View(users);
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

        public IActionResult FeedbackDetail()
        {
            return View();
        }
    }
}
