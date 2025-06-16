using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using SmartLicense_AdminSide.Models;
using SmartLicense_AdminSide.Services;
using MongoDB.Bson;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication;

namespace SmartLicense_AdminPanel.Controllers
{
    public class HomeController : Controller
    {
        private readonly IMongoCollection<User> _usersCollection;
        private readonly IMongoDatabase _database;
        private readonly ChatService _chatService;

        public HomeController(IMongoClient mongoClient, ChatService chatService)
        {
            var database = mongoClient.GetDatabase("Liscence_system");
            _usersCollection = database.GetCollection<User>("users");
            _database = database;
            _chatService = chatService;
        }

        public async Task<IActionResult> Index()
        {
            var users = await _usersCollection.Find(u => true).ToListAsync();
            return View(users);
        }

        public async Task<IActionResult> Test(string cnic)
        {
            if (string.IsNullOrEmpty(cnic))
                return RedirectToAction("Index");

            var user = await _usersCollection.Find(x => x.CNIC == cnic).FirstOrDefaultAsync();
            if (user == null)
                return RedirectToAction("Index");

            return View(user);
        }

        public async Task<IActionResult> Feedback()
        {
            var conversationCollection = _database.GetCollection<BsonDocument>("conversations");
            var pipeline = new BsonDocument[]
            {
                new BsonDocument("$lookup",
                    new BsonDocument
                    {
                        { "from", "users" },
                        { "localField", "userId" },
                        { "foreignField", "_id" },
                        { "as", "userDetails" }
                    }
                ),
                new BsonDocument("$unwind", "$userDetails"),
                new BsonDocument("$group",
                    new BsonDocument
                    {
                        { "_id", "$userId" },
                        { "name", new BsonDocument("$first", "$userDetails.name") },
                        { "cnic", new BsonDocument("$first", "$userDetails.cnic") },
                        { "conversationCount", new BsonDocument("$sum", 1) }
                    }
                )
            };

            var results = await conversationCollection.Aggregate<BsonDocument>(pipeline).ToListAsync();

            var conversationList = results.Select(doc => new
            {
                UserId = doc["_id"].ToString(),
                Name = doc.Contains("name") && doc["name"].IsString ? doc["name"].AsString : "Unknown",
                CNIC = doc.Contains("cnic") && doc["cnic"].IsString ? doc["cnic"].AsString : "Unknown",
                Count = doc.Contains("conversationCount") && doc["conversationCount"].IsInt32
                    ? doc["conversationCount"].AsInt32
                    : 0
            }).ToList();

            return View(conversationList);
        }

        public async Task<IActionResult> FeedbackDetail(string userId)
        {
            if (string.IsNullOrEmpty(userId))
                return RedirectToAction("Feedback");

            try
            {
                // Get user information
                var user = await _chatService.GetUserAsync(userId);
                if (user == null)
                    return RedirectToAction("Feedback");

                // Get or create conversation and load messages
                var conversation = await _chatService.GetOrCreateConversationAsync(userId);
                var messages = await _chatService.GetConversationMessagesAsync(userId);

                var model = new FeedbackDetailViewModel
                {
                    UserId = userId,
                    UserName = user.Name ?? "Unknown",
                    UserCNIC = user.CNIC ?? "Unknown",
                    Messages = messages
                };
                return View(model);
            }
            catch (Exception ex)
            {
                // Log error and redirect
                Console.WriteLine($"Error in FeedbackDetail: {ex.Message}");
                return RedirectToAction("Feedback");
            }
        }

        [HttpPost]
        public async Task<IActionResult> SendReply(string userId, string message)
        {
            // This method is now deprecated in favor of SignalR real-time messaging
            // We'll keep it as a fallback for non-SignalR clients
            if (string.IsNullOrEmpty(userId) || string.IsNullOrEmpty(message))
                return RedirectToAction("Feedback");

            var objectId = new ObjectId(userId);
            
            // Find the conversation
            var conversationFilter = Builders<BsonDocument>.Filter.Eq("userId", objectId);
            var conversation = await _database.GetCollection<BsonDocument>("conversations")
                .Find(conversationFilter)
                .FirstOrDefaultAsync();
            
            if (conversation == null)
            {
                return RedirectToAction("FeedbackDetail", new { userId });
            }
            
            var conversationId = conversation["_id"].AsObjectId;
            
            // Add the admin reply
            var newMessage = new BsonDocument
            {
                { "conversationId", conversationId },
                { "message", message },
                { "sentAt", DateTime.UtcNow },
                { "isAdminMessage", true }
            };
            
            await _database.GetCollection<BsonDocument>("messages").InsertOneAsync(newMessage);
            
            // Update the last updated time of the conversation
            var update = Builders<BsonDocument>.Update.Set("lastUpdatedAt", DateTime.UtcNow);
            await _database.GetCollection<BsonDocument>("conversations").UpdateOneAsync(
                Builders<BsonDocument>.Filter.Eq("_id", conversationId),
                update
            );
            
            return RedirectToAction("FeedbackDetail", new { userId });
        }

        public async Task<IActionResult> Logout()
        {
            // Sign out the user by clearing the authentication cookie
            await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);

            // Redirect to the Login action in AuthController
            return RedirectToAction("Login", "Auth");
        }

        public async Task<IActionResult> Violations(string cnic)
        {
            if (string.IsNullOrEmpty(cnic))
                return RedirectToAction("Index");

            var user = await _usersCollection.Find(x => x.CNIC == cnic).FirstOrDefaultAsync();
            if (user == null)
                return RedirectToAction("Index");

            // Get violations for this user
            var violationsCollection = _database.GetCollection<Violation>("violations");
            var violations = await violationsCollection
                .Find(v => v.UserCnic == cnic)
                .SortByDescending(v => v.TestDate)
                .ToListAsync();

            ViewBag.User = user;
            return View(violations);
        }

        public async Task<IActionResult> ViolationDetails(string id)
        {
            if (string.IsNullOrEmpty(id))
                return RedirectToAction("Index");

            var violationsCollection = _database.GetCollection<Violation>("violations");
            var violation = await violationsCollection
                .Find(v => v.Id == id)
                .FirstOrDefaultAsync();

            if (violation == null)
                return RedirectToAction("Index");

            return View(violation);
        }

        public async Task<IActionResult> ViolationReport(string cnic)
        {
            if (string.IsNullOrEmpty(cnic))
                return RedirectToAction("Index");

            var user = await _usersCollection.Find(x => x.CNIC == cnic).FirstOrDefaultAsync();
            if (user == null)
                return RedirectToAction("Index");

            // Get violations for this user
            var violationsCollection = _database.GetCollection<Violation>("violations");
            var violations = await violationsCollection
                .Find(v => v.UserCnic == cnic)
                .SortByDescending(v => v.TestDate)
                .ToListAsync();

            // Generate violation summary
            var violationSummary = new
            {
                TotalViolations = violations.Count,
                HighSeverityCount = violations.Count(v => v.Severity == "high"),
                MediumSeverityCount = violations.Count(v => v.Severity == "medium"),
                LowSeverityCount = violations.Count(v => v.Severity == "low"),
                ViolationsByType = violations
                    .GroupBy(v => v.Type)
                    .ToDictionary(g => g.Key, g => g.Count()),
                RecentViolations = violations.Take(10).ToList()
            };
            ViewBag.User = user;
            ViewBag.ViolationSummary = violationSummary;
            return View(violations);
        }

        [HttpGet]
        public async Task<IActionResult> GetViolationsPreview(string cnic)
        {
            try
            {
                if (string.IsNullOrEmpty(cnic))
                {
                    return Json(new { success = false, message = "CNIC is required" });
                }

                // Get violations for this user
                var violationsCollection = _database.GetCollection<Violation>("violations");
                var violations = await violationsCollection
                    .Find(v => v.UserCnic == cnic)
                    .SortByDescending(v => v.TestDate)
                    .Limit(10) // Get only the most recent 10 violations for preview
                    .ToListAsync();

                // Create summary
                var summary = new
                {
                    total = violations.Count,
                    high = violations.Count(v => v.Severity == "high"),
                    medium = violations.Count(v => v.Severity == "medium"),
                    low = violations.Count(v => v.Severity == "low")
                };

                // Create simplified violation data for preview
                var violationData = violations.Select(v => new
                {
                    type = v.Type,
                    severity = v.Severity,
                    description = v.Description,
                    timestamp = v.Timestamp
                }).ToList();

                return Json(new
                {
                    success = true,
                    violations = violationData,
                    summary = summary
                });
            }
            catch (Exception)
            {
                // Log the exception if you have logging configured
                return Json(new { success = false, message = "Error loading violations data" });
            }
        }

        [HttpPost]
        public async Task<IActionResult> CreateTestUser()
        {
            try
            {
                var testUser = new User
                {
                    Id = ObjectId.GenerateNewId().ToString(),
                    Name = "Test User",
                    CNIC = "12345-6789012-3",
                    Address = "Test Address",
                    Contact = "123-456-7890",
                    FatherName = "Test Father",
                    MotherName = "Test Mother"
                };

                await _usersCollection.InsertOneAsync(testUser);

                return Json(new { success = true, userId = testUser.Id, message = "Test user created successfully" });
            }
            catch (Exception ex)
            {
                return Json(new { success = false, message = "Failed to create test user: " + ex.Message });
            }
        }
    }
}