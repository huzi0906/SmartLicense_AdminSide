using MongoDB.Bson;
using MongoDB.Driver;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using SmartLicense_AdminSide.Models;

namespace SmartLicense_AdminSide.Services
{
    public class ChatService
    {
        private readonly IMongoCollection<Conversation> _conversationsCollection;
        private readonly IMongoCollection<ConversationMessage> _messagesCollection;
        private readonly IMongoCollection<User> _usersCollection;

        public ChatService(IMongoDatabase database)
        {
            _conversationsCollection = database.GetCollection<Conversation>("conversations");
            _messagesCollection = database.GetCollection<ConversationMessage>("messages");
            _usersCollection = database.GetCollection<User>("users");
        }

        public async Task<User> GetUserAsync(string userId)
        {
            return await _usersCollection.Find(u => u.Id == userId).FirstOrDefaultAsync();
        }

        public async Task<ConversationMessage> SaveMessageAsync(string userId, string message, bool isAdminMessage)
        {
            // Get or create the conversation for the user
            var conversation = await GetOrCreateConversationAsync(userId);

            // Create the new message
            var newMessage = new ConversationMessage
            {
                Id = ObjectId.GenerateNewId().ToString(),
                ConversationId = conversation.Id,
                Message = message,
                SentAt = DateTime.UtcNow,
                IsAdminMessage = isAdminMessage
            };

            // Save the message to the database
            await _messagesCollection.InsertOneAsync(newMessage);

            // Update the conversation's lastUpdatedAt timestamp
            var update = Builders<Conversation>.Update.Set(c => c.LastUpdatedAt, DateTime.UtcNow);
            await _conversationsCollection.UpdateOneAsync(c => c.Id == conversation.Id, update);

            return newMessage;
        }

        public async Task<Conversation> GetOrCreateConversationAsync(string userId)
        {
            // Try to find an existing conversation
            var conversation = await _conversationsCollection
                .Find(c => c.UserId == userId)
                .FirstOrDefaultAsync();

            if (conversation == null)
            {
                // Create a new conversation if none exists
                conversation = new Conversation
                {
                    Id = ObjectId.GenerateNewId().ToString(),
                    UserId = userId,
                    CreatedAt = DateTime.UtcNow,
                    LastUpdatedAt = DateTime.UtcNow,
                    Messages = new List<ConversationMessage>()
                };
                await _conversationsCollection.InsertOneAsync(conversation);
            }

            return conversation;
        }

        public async Task<List<ConversationMessage>> GetConversationMessagesAsync(string userId)
        {
            var conversation = await _conversationsCollection
                .Find(c => c.UserId == userId)
                .FirstOrDefaultAsync();

            if (conversation == null)
            {
                return new List<ConversationMessage>();
            }

            var messages = await _messagesCollection
                .Find(m => m.ConversationId == conversation.Id)
                .SortBy(m => m.SentAt)
                .ToListAsync();

            return messages;
        }
    }
}