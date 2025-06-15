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
        private readonly IMongoCollection<Conversation> _conversationsCollection;
        private readonly IMongoCollection<User> _usersCollection;

        public ChatService(IMongoClient mongoClient)
        {
            var database = mongoClient.GetDatabase("Liscence_system");
            _conversationsCollection = database.GetCollection<Conversation>("conversations");
            _usersCollection = database.GetCollection<User>("users");
        }

        public async Task<Conversation> GetOrCreateConversationAsync(string userId)
        {
            var conversation = await _conversationsCollection
                .Find(c => c.UserId == userId)
                .FirstOrDefaultAsync();

            if (conversation == null)
            {
                conversation = new Conversation
                {
                    UserId = userId,
                    CreatedAt = DateTime.UtcNow,
                    LastUpdatedAt = DateTime.UtcNow,
                    Messages = new List<ConversationMessage>()
                };

                await _conversationsCollection.InsertOneAsync(conversation);
            }

            return conversation;
        }

        public async Task<ConversationMessage> SaveMessageAsync(string userId, string message, bool isAdminMessage)
        {
            var conversation = await GetOrCreateConversationAsync(userId);
            
            var newMessage = new ConversationMessage
            {
                Id = ObjectId.GenerateNewId().ToString(),
                Message = message,
                IsAdminMessage = isAdminMessage,
                SentAt = DateTime.UtcNow
            };

            var update = Builders<Conversation>.Update
                .Push(c => c.Messages, newMessage)
                .Set(c => c.LastUpdatedAt, DateTime.UtcNow);

            await _conversationsCollection.UpdateOneAsync(
                c => c.Id == conversation.Id,
                update
            );

            return newMessage;
        }

        public async Task<List<ConversationMessage>> GetConversationMessagesAsync(string userId)
        {
            var conversation = await _conversationsCollection
                .Find(c => c.UserId == userId)
                .FirstOrDefaultAsync();

            return conversation?.Messages ?? new List<ConversationMessage>();
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
            return await _conversationsCollection
                .Find(_ => true)
                .SortByDescending(c => c.LastUpdatedAt)
                .Limit(limit)
                .ToListAsync();
        }
    }
}
