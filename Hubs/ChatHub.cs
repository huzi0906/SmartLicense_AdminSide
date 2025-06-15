using Microsoft.AspNetCore.SignalR;
using SmartLicense_AdminSide.Services;
using SmartLicense_AdminSide.Models;
using System;
using System.Threading.Tasks;

namespace SmartLicense_AdminSide.Hubs
{
    public class ChatHub : Hub
    {
        private readonly ChatService _chatService;

        public ChatHub(ChatService chatService)
        {
            _chatService = chatService;
        }

        public override async Task OnConnectedAsync()
        {
            await Clients.Caller.SendAsync("Connected", Context.ConnectionId);
            await base.OnConnectedAsync();
        }

        public override async Task OnDisconnectedAsync(Exception? exception)
        {
            await base.OnDisconnectedAsync(exception);
        }

        public async Task JoinConversation(string userId)
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, $"conversation_{userId}");
            await Clients.Caller.SendAsync("JoinedConversation", userId);
        }

        public async Task LeaveConversation(string userId)
        {
            await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"conversation_{userId}");
        }

        public async Task SendMessage(string userId, string message, bool isAdminMessage)
        {
            try
            {
                // Save message to database
                var savedMessage = await _chatService.SaveMessageAsync(userId, message, isAdminMessage);
                
                // Get user information for display
                var user = await _chatService.GetUserAsync(userId);
                var senderName = isAdminMessage ? "Administrator" : (user?.Name ?? "User");

                // Prepare message data for clients
                var messageData = new
                {
                    message = savedMessage.Message,
                    isAdminMessage = savedMessage.IsAdminMessage,
                    senderName = senderName,
                    sentAt = savedMessage.SentAt.ToString("MMM dd, yyyy HH:mm")
                };

                // Send to all clients in the conversation group
                await Clients.Group($"conversation_{userId}")
                    .SendAsync("ReceiveMessage", messageData);
            }
            catch (Exception ex)
            {
                await Clients.Caller.SendAsync("Error", $"Failed to send message: {ex.Message}");
            }
        }
    }
}
