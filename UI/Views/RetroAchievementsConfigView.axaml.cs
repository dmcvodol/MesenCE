using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Markup.Xaml;
using Mesen.RetroAchievements;
using Mesen.ViewModels;

namespace Mesen.Views
{
	public class RetroAchievementsConfigView : UserControl
	{
		public RetroAchievementsConfigView()
		{
			AvaloniaXamlLoader.Load(this);
		}

		private void Login_OnClick(object? sender, RoutedEventArgs e)
		{
			TextBox? passwordInput = this.FindControl<TextBox>("PasswordInput");
			TextBlock? loginStatus = this.FindControl<TextBlock>("LoginStatus");
			if(DataContext is not RetroAchievementsConfigViewModel vm || passwordInput == null || loginStatus == null) {
				return;
			}

			string username = vm.Config.Username?.Trim() ?? "";
			string password = passwordInput.Text ?? "";
			loginStatus.Text = "Signing in...";

			if(RetroAchievementsManager.Instance.TryLoginWithPassword(username, password, out string token, out string error)) {
				vm.Config.Username = username;
				vm.Config.Token = token;
				vm.Config.Enabled = true;
				passwordInput.Text = "";
				loginStatus.Text = "Signed in. Press OK to save the login token.";
			} else {
				loginStatus.Text = "Login failed: " + error;
			}
		}
	}
}
