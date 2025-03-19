using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using SmartLicense_AdminSide.Models;
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

        public HomeController(IMongoClient mongoClient)
        {
            var database = mongoClient.GetDatabase("Liscence_system");
            _usersCollection = database.GetCollection<User>("users");
            _database = database;
        }

        public async Task<IActionResult> Index()
        {
            var users = await _usersCollection.Find(_ => true).ToListAsync();
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

            var objectId = new ObjectId(userId);
            
            var userCollection = _database.GetCollection<BsonDocument>("users");
            var messageCollection = _database.GetCollection<BsonDocument>("messages");
            
            var user = await userCollection.Find(Builders<BsonDocument>.Filter.Eq("_id", objectId)).FirstOrDefaultAsync();
            if (user == null)
                return RedirectToAction("Feedback");
            
            // Safely handle 'name' and 'cnic'
            var userName = user.Contains("name") && user["name"].BsonType == BsonType.String 
                ? user["name"].AsString 
                : "Unknown";
            var userCnic = user.Contains("cnic") && user["cnic"].BsonType == BsonType.String 
                ? user["cnic"].AsString 
                : "Unknown";

            // Check if conversation exists, if not, we'll create a new one
            var conversationFilter = Builders<BsonDocument>.Filter.Eq("userId", objectId);
            var conversation = await _database.GetCollection<BsonDocument>("conversations")
                .Find(conversationFilter)
                .FirstOrDefaultAsync();
            
            List<ConversationMessage> messages = new List<ConversationMessage>();
            string conversationId;
            
            if (conversation == null)
            {
                // Convert existing feedback to conversation messages
                var feedbackCollection = _database.GetCollection<BsonDocument>("feedbacks");
                var feedbacksCursor = await feedbackCollection
                    .Find(Builders<BsonDocument>.Filter.Eq("userId", objectId))
                    .SortBy(f => f["submittedAt"])
                    .ToListAsync();
                
                // Create a new conversation
                var newConversation = new BsonDocument
                {
                    { "userId", objectId },
                    { "createdAt", DateTime.UtcNow },
                    { "lastUpdatedAt", DateTime.UtcNow }
                };
                
                await _database.GetCollection<BsonDocument>("conversations").InsertOneAsync(newConversation);
                conversationId = newConversation["_id"].AsObjectId.ToString();
                
                // Add the old feedback messages to the new conversation system
                foreach (var feedback in feedbacksCursor)
                {
                    var newMessage = new BsonDocument
                    {
                        { "conversationId", new ObjectId(conversationId) },
                        { "message", feedback["feedback"].AsString },
                        { "sentAt", feedback["submittedAt"] },
                        { "isAdminMessage", false }
                    };
                    
                    await messageCollection.InsertOneAsync(newMessage);
                    
                    messages.Add(new ConversationMessage 
                    {
                        Id = newMessage["_id"].AsObjectId.ToString(),
                        ConversationId = conversationId,
                        Message = newMessage["message"].AsString,
                        SentAt = newMessage["sentAt"].ToUniversalTime(),
                        IsAdminMessage = false
                    });
                }
            }
            else
            {
                conversationId = conversation["_id"].AsObjectId.ToString();
                
                // Fetch existing messages
                var messagesCursor = await messageCollection
                    .Find(Builders<BsonDocument>.Filter.Eq("conversationId", new ObjectId(conversationId)))
                    .SortBy(m => m["sentAt"])
                    .ToListAsync();
                    
                foreach (var message in messagesCursor)
                {
                    messages.Add(new ConversationMessage
                    {
                        Id = message["_id"].AsObjectId.ToString(),
                        ConversationId = conversationId,
                        Message = message["message"].AsString,
                        SentAt = message["sentAt"].ToUniversalTime(),
                        IsAdminMessage = message["isAdminMessage"].AsBoolean
                    });
                }
            }
            
            var model = new FeedbackDetailViewModel
            {
                UserId = userId,
                UserName = userName,
                UserCNIC = userCnic,
                Messages = messages
            };
            
            return View(model);
        }

        [HttpPost]
        public async Task<IActionResult> SendReply(string userId, string message)
        {
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
    }
}
