// CHat service
using MongoDB.Driver;
using SmartLicense_AdminSide.Models;
using MongoDB.Bson;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace SmartLicense_AdminSide.Services
{
    public class ChatService
    {
        private readonly IMongoCollection<BsonDocument> _conversationsCollection;
        private readonly IMongoCollection<BsonDocument> _messagesCollection;
        private readonly IMongoCollection<User> _usersCollection;
        private readonly IMongoDatabase _database;

        public ChatService(IMongoClient mongoClient)
        {
            _database = mongoClient.GetDatabase("Liscence_system");
            _conversationsCollection = _database.GetCollection<BsonDocument>("conversations");
            _messagesCollection = _database.GetCollection<BsonDocument>("messages");
            _usersCollection = _database.GetCollection<User>("users");
        }

        public async Task<Conversation> GetOrCreateConversationAsync(string userId)
        {
            var userObjectId = new ObjectId(userId);
            var conversationDocument = await _conversationsCollection
                .Find(Builders<BsonDocument>.Filter.Eq("userId", userObjectId))
                .FirstOrDefaultAsync();

            if (conversationDocument == null)
            {
                var newConversationDocument = new BsonDocument
                {
                    { "userId", userObjectId },
                    { "createdAt", DateTime.UtcNow },
                    { "lastUpdatedAt", DateTime.UtcNow }
                };

                await _conversationsCollection.InsertOneAsync(newConversationDocument);
                conversationDocument = newConversationDocument;
            }

            // Convert BsonDocument to Conversation model
            var conversation = new Conversation
            {
                Id = conversationDocument["_id"].AsObjectId.ToString(),
                UserId = userId,
                CreatedAt = conversationDocument["createdAt"].ToUniversalTime(),
                LastUpdatedAt = conversationDocument["lastUpdatedAt"].ToUniversalTime(),
                Messages = new List<ConversationMessage>()
            };

            return conversation;
        }

        public async Task<ConversationMessage> SaveMessageAsync(string userId, string message, bool isAdminMessage)
        {
            var conversation = await GetOrCreateConversationAsync(userId);
            
            var newMessage = new ConversationMessage
            {
                Id = ObjectId.GenerateNewId().ToString(),
                ConversationId = conversation.Id,
                Message = message,
                IsAdminMessage = isAdminMessage,
                SentAt = DateTime.UtcNow
            };

            // Save message to messages collection
            var messageDocument = new BsonDocument
            {
                { "conversationId", new ObjectId(conversation.Id) },
                { "message", message },
                { "isAdminMessage", isAdminMessage },
                { "sentAt", DateTime.UtcNow }
            };

            await _messagesCollection.InsertOneAsync(messageDocument);

            // Update conversation's lastUpdatedAt
            var conversationFilter = Builders<BsonDocument>.Filter.Eq("_id", new ObjectId(conversation.Id));
            var conversationUpdate = Builders<BsonDocument>.Update.Set("lastUpdatedAt", DateTime.UtcNow);
            await _conversationsCollection.UpdateOneAsync(conversationFilter, conversationUpdate);

            return newMessage;
        }

        public async Task<List<ConversationMessage>> GetConversationMessagesAsync(string userId)
        {
            // First get the conversation
            var userObjectId = new ObjectId(userId);
            var conversationDocument = await _conversationsCollection
                .Find(Builders<BsonDocument>.Filter.Eq("userId", userObjectId))
                .FirstOrDefaultAsync();

            if (conversationDocument == null)
            {
                return new List<ConversationMessage>();
            }

            var conversationId = conversationDocument["_id"].AsObjectId;
            
            // Get messages for this conversation
            var messageDocuments = await _messagesCollection
                .Find(Builders<BsonDocument>.Filter.Eq("conversationId", conversationId))
                .Sort(Builders<BsonDocument>.Sort.Ascending("sentAt"))
                .ToListAsync();

            var messages = new List<ConversationMessage>();
            foreach (var doc in messageDocuments)
            {
                var message = new ConversationMessage
                {
                    Id = doc["_id"].AsObjectId.ToString(),
                    ConversationId = conversationId.ToString(),
                    Message = doc["message"].AsString,
                    IsAdminMessage = doc.Contains("isAdminMessage") ? doc["isAdminMessage"].AsBoolean : false,
                    SentAt = doc["sentAt"].ToUniversalTime()
                };
                messages.Add(message);
            }

            return messages;
        }

        public async Task<User> GetUserAsync(string userId)
        {
            return await _usersCollection
                .Find(u => u.Id == userId)
                .FirstOrDefaultAsync();
        }

        public async Task<User> GetUserByCnicAsync(string cnic)
        {
            return await _usersCollection
                .Find(u => u.CNIC == cnic)
                .FirstOrDefaultAsync();
        }

        public async Task<List<Conversation>> GetRecentConversationsAsync(int limit = 50)
        {
            var conversationDocuments = await _conversationsCollection
                .Find(Builders<BsonDocument>.Filter.Empty)
                .Sort(Builders<BsonDocument>.Sort.Descending("lastUpdatedAt"))
                .Limit(limit)
                .ToListAsync();

            var conversations = new List<Conversation>();
            foreach (var doc in conversationDocuments)
            {
                var conversation = new Conversation
                {
                    Id = doc["_id"].AsObjectId.ToString(),
                    UserId = doc["userId"].AsObjectId.ToString(),
                    CreatedAt = doc["createdAt"].ToUniversalTime(),
                    LastUpdatedAt = doc["lastUpdatedAt"].ToUniversalTime(),
                    Messages = new List<ConversationMessage>()
                };
                conversations.Add(conversation);
            }

            return conversations;
        }
    }
}