using CommunityToolkit.Mvvm.ComponentModel;

namespace Mesen.Config
{
	public partial class RetroAchievementsConfig : BaseConfig<RetroAchievementsConfig>
	{
		[ObservableProperty] public partial bool Enabled { get; set; } = false;
		[ObservableProperty] public partial string Username { get; set; } = "";
		[ObservableProperty] public partial string Token { get; set; } = "";
		[ObservableProperty] public partial bool HardcoreMode { get; set; } = false;
		[ObservableProperty] public partial bool ShowUnlockNotifications { get; set; } = true;
		[ObservableProperty] public partial bool EnableLeaderboards { get; set; } = true;
		[ObservableProperty] public partial bool EnableRichPresence { get; set; } = true;

		public void ApplyConfig()
		{
			// Runtime RetroAchievements integration will be connected here.
		}
	}
}
