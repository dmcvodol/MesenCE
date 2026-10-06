using CommunityToolkit.Mvvm.ComponentModel;

namespace Mesen.Config
{
	public partial class Configuration
	{
		[ObservableProperty] public partial RetroAchievementsConfig RetroAchievements { get; set; } = new();
	}
}
