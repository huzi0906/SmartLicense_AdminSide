using System.Collections.Generic;

namespace SmartLicense_AdminSide.Models
{
    public class FeedbackDetailViewModel
    {
        public required string UserId { get; set; }
        public required string UserName { get; set; }
        public required string UserCNIC { get; set; }
        public required List<ConversationMessage> Messages { get; set; }
    }
}
