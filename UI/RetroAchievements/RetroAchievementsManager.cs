using Mesen.Config;
using Mesen.Interop;
using System;

namespace Mesen.RetroAchievements
{
	/// <summary>
	/// Owns the RetroAchievements runtime lifecycle for the standalone MesenCE frontend.
	/// The actual rc_client bridge is added in the native integration layer; this class
	/// already tracks the Mesen game/frame lifecycle so the bridge has one stable entry point.
	/// </summary>
	public sealed class RetroAchievementsManager : IDisposable
	{
		public static RetroAchievementsManager Instance { get; } = new();

		private readonly NotificationListener _notifications;
		private bool _gameLoaded;

		private RetroAchievementsManager()
		{
			_notifications = new NotificationListener();
			_notifications.OnNotification += OnNotification;
		}

		private bool Enabled => ConfigManager.Config.RetroAchievements.Enabled;

		private void OnNotification(NotificationEventArgs e)
		{
			if(!Enabled && e.NotificationType != ConsoleNotificationType.BeforeGameUnload && e.NotificationType != ConsoleNotificationType.EmulationStopped) {
				return;
			}

			switch(e.NotificationType) {
				case ConsoleNotificationType.GameLoaded:
					_gameLoaded = true;
					OnGameLoaded();
					break;

				case ConsoleNotificationType.PpuFrameDone:
					if(_gameLoaded) {
						OnFrame();
					}
					break;

				case ConsoleNotificationType.GameReset:
					if(_gameLoaded) {
						OnReset();
					}
					break;

				case ConsoleNotificationType.StateLoaded:
					if(_gameLoaded) {
						OnStateLoaded();
					}
					break;

				case ConsoleNotificationType.BeforeGameUnload:
				case ConsoleNotificationType.EmulationStopped:
					if(_gameLoaded) {
						OnGameUnloaded();
						_gameLoaded = false;
					}
					break;
			}
		}

		private static void OnGameLoaded()
		{
			// TODO: call rc_client_begin_identify_and_load_game through the native bridge.
		}

		private static void OnFrame()
		{
			// TODO: call rc_client_do_frame through the native bridge.
		}

		private static void OnReset()
		{
			// rc_client keeps the active game; reset-specific state handling is added with the bridge.
		}

		private static void OnStateLoaded()
		{
			// Hardcore mode will reject state loading. Softcore mode will notify rc_client here.
		}

		private static void OnGameUnloaded()
		{
			// TODO: unload the active rc_client game through the native bridge.
		}

		public void Dispose()
		{
			_notifications.OnNotification -= OnNotification;
			_notifications.Dispose();
		}
	}
}
