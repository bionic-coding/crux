# API surface

_1934 interfaces (public, package or open declarations, and every protocol), 185 protocol requirements, 20 package products and 3 `@main` declarations, read through the pinned Swift grammar; nothing was compiled or executed._

## Interfaces

| interface | kind | access | declared at | attributes | conditional |
|---|---|---|---|---|---|
| `ErrorHandler.present(_:)` | func | public | `Mac/ErrorHandler.swift:18-18` | @Sendable | — |
| `ErrorHandler.log(_:)` | func | public | `Mac/ErrorHandler.swift:24-24` | — | — |
| `Inspector` | protocol | internal | `Mac/Inspector/InspectorWindowController.swift:11-11` | @MainActor | — |
| `AddFeedWindowControllerDelegate` | protocol | internal | `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:15-15` | @MainActor | — |
| `DetailWebViewControllerDelegate` | protocol | internal | `Mac/MainWindow/Detail/DetailWebViewController.swift:16-16` | @MainActor | — |
| `DetailWebViewController.webView(_:didCommit:)` | func | public | `Mac/MainWindow/Detail/DetailWebViewController.swift:247-247` | — | — |
| `DetailWebViewController.webView(_:didFinish:)` | func | public | `Mac/MainWindow/Detail/DetailWebViewController.swift:264-264` | — | — |
| `MainWindowController.validateUserInterfaceItem(_:)` | func | public | `Mac/MainWindow/MainWindowController.swift:253-253` | — | — |
| `Feed.pasteboardWriter` | var | public | `Mac/MainWindow/Sidebar/PasteboardFeed.swift:156-156` | — | — |
| `Folder.pasteboardWriter` | var | public | `Mac/MainWindow/Sidebar/PasteboardFolder.swift:87-87` | — | — |
| `RenameWindowControllerDelegate` | protocol | internal | `Mac/MainWindow/Sidebar/Renaming/RenameWindowController.swift:11-11` | @MainActor | — |
| `Notification.Name.DidUpdateFeedPreferencesFromContextMenu` | let | public | `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:16-16` | — | — |
| `SidebarDelegate` | protocol | internal | `Mac/MainWindow/Sidebar/SidebarViewController.swift:20-20` | @MainActor | — |
| `SidebarViewController.menuNeedsUpdate(_:)` | func | public | `Mac/MainWindow/Sidebar/SidebarViewController.swift:408-408` | — | — |
| `Article.pasteboardWriter` | var | public | `Mac/MainWindow/Timeline/ArticlePasteboardWriter.swift:14-14` | — | — |
| `NSEdgeInsets.==(lhs:rhs:)` | func | public | `Mac/MainWindow/Timeline/Cell/TimelineCellAppearance.swift:68-68` | — | — |
| `TimelineContainerViewControllerDelegate` | protocol | internal | `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:13-13` | @MainActor | — |
| `TimelineDelegate` | protocol | internal | `Mac/MainWindow/Timeline/TimelineViewController.swift:16-16` | @MainActor | — |
| `TimelineViewController.menuNeedsUpdate(_:)` | func | public | `Mac/MainWindow/Timeline/TimelineViewController.swift:879-879` | — | — |
| `AccountsDetailViewController.init(coder:)` | init | public | `Mac/Preferences/Accounts/AccountsDetailViewController.swift:23-23` | — | — |
| `AccountsPreferencesAddAccountDelegate` | protocol | internal | `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:15-15` | @MainActor | — |
| `GeneralPreferencesViewController.init(nibName:bundle:)` | init | public | `Mac/Preferences/General/GeneralPrefencesViewController.swift:25-25` | — | — |
| `GeneralPreferencesViewController.init(coder:)` | init | public | `Mac/Preferences/General/GeneralPrefencesViewController.swift:30-30` | — | — |
| `AppDelegateAppleEvents` | protocol | internal | `Mac/Scripting/AppDelegate+Scriptability.swift:23-23` | @MainActor | — |
| `ScriptingAppDelegate` | protocol | internal | `Mac/Scripting/AppDelegate+Scriptability.swift:28-28` | @MainActor | — |
| `ScriptingMainWindowController` | protocol | internal | `Mac/Scripting/MainWindowController+Scriptability.swift:13-13` | @MainActor | — |
| `ScriptingObject` | protocol | internal | `Mac/Scripting/ScriptingObject.swift:11-11` | — | — |
| `NamedScriptingObject` | protocol | internal | `Mac/Scripting/ScriptingObject.swift:16-16` | — | — |
| `UniqueIDScriptingObject` | protocol | internal | `Mac/Scripting/ScriptingObject.swift:20-20` | — | — |
| `ScriptingObjectContainer` | protocol | internal | `Mac/Scripting/ScriptingObjectContainer.swift:12-12` | — | — |
| `Notification.Name.UserDidAddAccount` | let | public | `Modules/Account/Sources/Account/Account.swift:28-28` | — | — |
| `Notification.Name.UserDidDeleteAccount` | let | public | `Modules/Account/Sources/Account/Account.swift:29-29` | — | — |
| `Notification.Name.AccountRefreshDidBegin` | let | public | `Modules/Account/Sources/Account/Account.swift:30-30` | — | — |
| `Notification.Name.AccountRefreshDidFinish` | let | public | `Modules/Account/Sources/Account/Account.swift:31-31` | — | — |
| `Notification.Name.AccountDidDownloadArticles` | let | public | `Modules/Account/Sources/Account/Account.swift:32-32` | — | — |
| `Notification.Name.AccountStateDidChange` | let | public | `Modules/Account/Sources/Account/Account.swift:33-33` | — | — |
| `Notification.Name.StatusesDidChange` | let | public | `Modules/Account/Sources/Account/Account.swift:34-34` | — | — |
| `Notification.Name.AccountDidQueueArticleStatuses` | let | public | `Modules/Account/Sources/Account/Account.swift:37-37` | — | — |
| `AccountType` | enum | public | `Modules/Account/Sources/Account/Account.swift:40-40` | — | — |
| `AccountType.isDeveloperRestricted` | var | public | `Modules/Account/Sources/Account/Account.swift:52-52` | — | — |
| `AccountType.displayName` | var | public | `Modules/Account/Sources/Account/Account.swift:56-56` | — | — |
| `FetchType` | enum | public | `Modules/Account/Sources/Account/Account.swift:81-81` | — | — |
| `Account` | class | public | `Modules/Account/Sources/Account/Account.swift:92-92` | @MainActor | — |
| `Account.UserInfoKey` | struct | public | `Modules/Account/Sources/Account/Account.swift:96-96` | — | — |
| `Account.UserInfoKey.account` | let | public | `Modules/Account/Sources/Account/Account.swift:97-97` | — | — |
| `Account.UserInfoKey.newArticles` | let | public | `Modules/Account/Sources/Account/Account.swift:98-98` | — | — |
| `Account.UserInfoKey.updatedArticles` | let | public | `Modules/Account/Sources/Account/Account.swift:99-99` | — | — |
| `Account.UserInfoKey.statuses` | let | public | `Modules/Account/Sources/Account/Account.swift:100-100` | — | — |
| `Account.UserInfoKey.articles` | let | public | `Modules/Account/Sources/Account/Account.swift:101-101` | — | — |
| `Account.UserInfoKey.articleIDs` | let | public | `Modules/Account/Sources/Account/Account.swift:102-102` | — | — |
| `Account.UserInfoKey.statusKey` | let | public | `Modules/Account/Sources/Account/Account.swift:103-103` | — | — |
| `Account.UserInfoKey.statusFlag` | let | public | `Modules/Account/Sources/Account/Account.swift:104-104` | — | — |
| `Account.UserInfoKey.feeds` | let | public | `Modules/Account/Sources/Account/Account.swift:105-105` | — | — |
| `Account.UserInfoKey.syncErrors` | let | public | `Modules/Account/Sources/Account/Account.swift:106-106` | — | — |
| `Account.isDeleted` | var | public | `Modules/Account/Sources/Account/Account.swift:109-109` | — | — |
| `Account.containerID` | var | public | `Modules/Account/Sources/Account/Account.swift:111-111` | — | — |
| `Account.account` | var | public | `Modules/Account/Sources/Account/Account.swift:115-115` | — | — |
| `Account.accountID` | let | public | `Modules/Account/Sources/Account/Account.swift:118-118` | — | — |
| `Account.type` | let | public | `Modules/Account/Sources/Account/Account.swift:119-119` | — | — |
| `Account.nameForDisplay` | var | public | `Modules/Account/Sources/Account/Account.swift:120-120` | — | — |
| `Account.activityOwner` | var | public | `Modules/Account/Sources/Account/Account.swift:127-127` | — | — |
| `Account.name` | var | public | `Modules/Account/Sources/Account/Account.swift:131-131` | — | — |
| `Account.defaultName` | let | public | `Modules/Account/Sources/Account/Account.swift:145-145` | — | — |
| `Account.isActive` | var | public | `Modules/Account/Sources/Account/Account.swift:147-147` | — | — |
| `Account.topLevelFeeds` | var | public | `Modules/Account/Sources/Account/Account.swift:161-161` | — | — |
| `Account.folders` | var | public | `Modules/Account/Sources/Account/Account.swift:162-162` | — | — |
| `Account.externalID` | var | public | `Modules/Account/Sources/Account/Account.swift:164-164` | — | — |
| `Account.sortedFolders` | var | public | `Modules/Account/Sources/Account/Account.swift:173-173` | — | — |
| `Account.lastArticleFetchStartTime` | var | public | `Modules/Account/Sources/Account/Account.swift:211-211` | — | — |
| `Account.lastRefreshCompletedDate` | var | public | `Modules/Account/Sources/Account/Account.swift:220-220` | — | — |
| `Account.endpointURL` | var | public | `Modules/Account/Sources/Account/Account.swift:229-229` | — | — |
| `Account.dataFolder` | let | public | `Modules/Account/Sources/Account/Account.swift:244-244` | — | — |
| `Account.unreadCount` | var | public | `Modules/Account/Sources/Account/Account.swift:262-262` | — | — |
| `Account.behaviors` | var | public | `Modules/Account/Sources/Account/Account.swift:270-270` | — | — |
| `Account.refreshInProgress` | var | public | `Modules/Account/Sources/Account/Account.swift:274-274` | — | — |
| `Account.progressInfo` | var | public | `Modules/Account/Sources/Account/Account.swift:287-287` | — | — |
| `Account.storeCredentials(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:358-358` | — | — |
| `Account.retrieveCredentials(type:)` | func | public | `Modules/Account/Sources/Account/Account.swift:374-374` | — | — |
| `Account.removeCredentials(type:)` | func | public | `Modules/Account/Sources/Account/Account.swift:392-392` | — | — |
| `Account.validateCredentials(type:credentials:endpoint:)` | func | public | `Modules/Account/Sources/Account/Account.swift:405-405` | — | — |
| `Account.oauthAuthorizationCodeGrantRequest(for:state:)` | func | public | `Modules/Account/Sources/Account/Account.swift:429-429` | — | — |
| `Account.requestOAuthAccessToken(with:client:accountType:)` | func | public | `Modules/Account/Sources/Account/Account.swift:441-441` | — | — |
| `Account.receiveRemoteNotification(userInfo:)` | func | public | `Modules/Account/Sources/Account/Account.swift:456-456` | — | — |
| `Account.triggerRefreshAll()` | func | public | `Modules/Account/Sources/Account/Account.swift:463-463` | — | — |
| `Account.refreshAll()` | func | public | `Modules/Account/Sources/Account/Account.swift:469-469` | — | — |
| `Account.logActivity(kind:detail:successMessage:durationIsSignificant:_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:475-476` | @discardableResult | — |
| `Account.logActivity(kind:detail:successMessage:durationIsSignificant:_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:487-488` | @discardableResult | — |
| `Account.sendArticleStatus()` | func | public | `Modules/Account/Sources/Account/Account.swift:506-506` | — | — |
| `Account.syncArticleStatus()` | func | public | `Modules/Account/Sources/Account/Account.swift:510-511` | @discardableResult | — |
| `Account.importOPML(_:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:517-517` | — | — |
| `Account.suspendNetwork()` | func | public | `Modules/Account/Sources/Account/Account.swift:538-538` | — | — |
| `Account.resumeDelegate()` | func | public | `Modules/Account/Sources/Account/Account.swift:543-543` | — | — |
| `Account.resume()` | func | public | `Modules/Account/Sources/Account/Account.swift:548-548` | — | — |
| `Account.save()` | func | public | `Modules/Account/Sources/Account/Account.swift:554-554` | — | — |
| `Account.saveIfNeeded()` | func | public | `Modules/Account/Sources/Account/Account.swift:560-560` | — | — |
| `Account.prepareForDeletion()` | func | public | `Modules/Account/Sources/Account/Account.swift:564-564` | — | — |
| `Account.markArticles(articleIDs:statusKey:flag:)` | func | public | `Modules/Account/Sources/Account/Account.swift:596-596` | — | — |
| `Account.existingContainers(withFeed:)` | func | public | `Modules/Account/Sources/Account/Account.swift:607-607` | — | — |
| `Account.ensureFolder(withFolderNames:)` | func | public | `Modules/Account/Sources/Account/Account.swift:642-642` | — | — |
| `Account.existingFolder(withDisplayName:)` | func | public | `Modules/Account/Sources/Account/Account.swift:652-652` | — | — |
| `Account.existingFolder(withExternalID:)` | func | public | `Modules/Account/Sources/Account/Account.swift:656-656` | — | — |
| `Account.addFeed(_:to:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:683-683` | — | — |
| `Account.createFeed(url:name:container:validateFeed:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:694-694` | — | — |
| `Account.removeFeed(_:from:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:728-728` | — | — |
| `Account.moveFeed(_:from:to:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:739-739` | — | — |
| `Account.renameFeed(_:name:)` | func | public | `Modules/Account/Sources/Account/Account.swift:750-750` | — | — |
| `Account.restoreFeed(_:container:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:754-754` | — | — |
| `Account.addFolder(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:765-766` | @discardableResult | — |
| `Account.removeFolder(_:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:770-770` | — | — |
| `Account.renameFolder(_:to:)` | func | public | `Modules/Account/Sources/Account/Account.swift:781-781` | — | — |
| `Account.restoreFolder(_:completion:)` | func | public | `Modules/Account/Sources/Account/Account.swift:785-785` | — | — |
| `Account.updateUnreadCounts(feeds:)` | func | public | `Modules/Account/Sources/Account/Account.swift:802-802` | — | — |
| `Account.fetchArticles(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:808-808` | — | — |
| `Account.fetchArticlesAsync(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:833-833` | — | — |
| `Account.fetchUnreadCountForStarredArticlesAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:858-858` | — | — |
| `Account.fetchCountForStarredArticles()` | func | public | `Modules/Account/Sources/Account/Account.swift:862-862` | — | — |
| `Account.fetchArticleCountsAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:866-866` | — | — |
| `Account.fetchLastUpdateDates()` | func | public | `Modules/Account/Sources/Account/Account.swift:871-871` | — | — |
| `Account.fetchUnreadCountForTodayAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:875-875` | — | — |
| `Account.fetchCountForTodayArticlesAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:879-879` | — | — |
| `Account.fetchCountForStarredArticlesAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:883-883` | — | — |
| `Account.fetchUnreadArticleIDsAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:887-887` | — | — |
| `Account.fetchStarredArticleIDsAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:891-891` | — | — |
| `Account.fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDateAsync()` | func | public | `Modules/Account/Sources/Account/Account.swift:896-896` | — | — |
| `Account.unreadCount(for:)` | func | public | `Modules/Account/Sources/Account/Account.swift:901-901` | — | — |
| `Account.setUnreadCount(_:for:)` | func | public | `Modules/Account/Sources/Account/Account.swift:905-905` | — | — |
| `Account.structureDidChange()` | func | public | `Modules/Account/Sources/Account/Account.swift:909-909` | — | — |
| `Account.flattenedFeeds()` | func | public | `Modules/Account/Sources/Account/Account.swift:1048-1048` | — | — |
| `Account.removeFeedFromTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1056-1056` | — | — |
| `Account.removeAllInstancesOfFeedFromTreeAtAllLevels(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1062-1062` | — | — |
| `Account.removeFeedsFromTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1075-1075` | — | — |
| `Account.addFeedToTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1084-1084` | — | — |
| `Account.vacuumDatabases()` | func | public | `Modules/Account/Sources/Account/Account.swift:1111-1111` | — | — |
| `Account.fetchCloudKitStats(progress:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1121-1121` | — | — |
| `Account.cleanUpCloudKit(progress:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1128-1128` | — | — |
| `Account.debugDropConditionalGetInfo()` | func | public | `Modules/Account/Sources/Account/Account.swift:1135-1135` | — | — |
| `Account.debugRunSearch()` | func | public | `Modules/Account/Sources/Account/Account.swift:1143-1143` | — | — |
| `Account.hash(into:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1192-1192` | — | — |
| `Account.==(lhs:rhs:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1198-1198` | — | — |
| `Account.existingFeed(withFeedID:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1567-1567` | — | — |
| `Account.existingFeed(withExternalID:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1571-1571` | — | — |
| `Account.OPMLString(indentLevel:allowCustomAttributes:)` | func | public | `Modules/Account/Sources/Account/Account.swift:1580-1580` | — | — |
| `AccountBehaviors` | typealias | public | `Modules/Account/Sources/Account/AccountBehaviors.swift:17-17` | — | — |
| `AccountBehavior` | enum | public | `Modules/Account/Sources/Account/AccountBehaviors.swift:19-19` | — | — |
| `AccountDelegate` | protocol | internal | `Modules/Account/Sources/Account/AccountDelegate.swift:15-15` | @MainActor | — |
| `AccountError` | enum | public | `Modules/Account/Sources/Account/AccountError.swift:12-12` | — | — |
| `AccountError.isCredentialsError` | var | public | `Modules/Account/Sources/Account/AccountError.swift:23-23` | — | — |
| `AccountError.account(from:)` | func | public | `Modules/Account/Sources/Account/AccountError.swift:36-36` | @MainActor | — |
| `AccountError.errorDescription` | var | public | `Modules/Account/Sources/Account/AccountError.swift:43-43` | — | — |
| `AccountError.recoverySuggestion` | var | public | `Modules/Account/Sources/Account/AccountError.swift:74-74` | — | — |
| `AccountManager` | class | public | `Modules/Account/Sources/Account/AccountManager.swift:18-18` | @MainActor | — |
| `AccountManager.shared` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:20-20` | — | — |
| `AccountManager.netNewsWireNewsURL` | let | public | `Modules/Account/Sources/Account/AccountManager.swift:22-22` | — | — |
| `AccountManager.defaultAccount` | let | public | `Modules/Account/Sources/Account/AccountManager.swift:25-25` | — | — |
| `AccountManager.errorLogDatabase` | let | public | `Modules/Account/Sources/Account/AccountManager.swift:26-26` | — | — |
| `AccountManager.isSuspended` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:37-37` | — | — |
| `AccountManager.syncArticleContentForUnreadArticles` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:41-41` | — | — |
| `AccountManager.areUnreadCountsInitialized` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:57-57` | — | — |
| `AccountManager.unreadCount` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:66-66` | — | — |
| `AccountManager.accounts` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:74-74` | — | — |
| `AccountManager.sortedAccounts` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:78-78` | — | — |
| `AccountManager.iCloudAccount` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:82-82` | — | — |
| `AccountManager.hasiCloudAccount` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:86-86` | — | — |
| `AccountManager.activeAccounts` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:90-90` | — | — |
| `AccountManager.repairStatusesIfNeeded()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:96-96` | — | — |
| `AccountManager.sortedActiveAccounts` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:106-106` | — | — |
| `AccountManager.lastRefreshCompletedDate` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:110-110` | — | — |
| `AccountManager.existingActiveAccount(forDisplayName:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:122-122` | — | — |
| `AccountManager.refreshInProgress` | var | public | `Modules/Account/Sources/Account/AccountManager.swift:126-126` | — | — |
| `AccountManager.init()` | init | public | `Modules/Account/Sources/Account/AccountManager.swift:137-137` | — | — |
| `AccountManager.start()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:166-166` | — | — |
| `AccountManager.createAccount(type:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:185-185` | — | — |
| `AccountManager.deleteAccount(_:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:212-212` | — | — |
| `AccountManager.duplicateServiceAccount(type:username:endpoint:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:238-238` | — | — |
| `AccountManager.existingAccount(accountID:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:254-254` | — | — |
| `AccountManager.existingContainer(with:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:258-258` | — | — |
| `AccountManager.existingFeed(with:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:270-270` | — | — |
| `AccountManager.suspendNetworkAll()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:286-286` | — | — |
| `AccountManager.resumeAll()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:293-293` | — | — |
| `AccountManager.receiveRemoteNotification(userInfo:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:303-303` | — | — |
| `AccountManager.ErrorHandlerCallback` | typealias | public | `Modules/Account/Sources/Account/AccountManager.swift:309-309` | — | — |
| `AccountManager.refreshAllWithoutWaiting(errorHandler:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:311-311` | — | — |
| `AccountManager.refreshAll(errorHandler:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:319-320` | @discardableResult | — |
| `AccountManager.sendArticleStatusAll()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:346-346` | — | — |
| `AccountManager.syncArticleStatusAllWithoutWaiting()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:356-356` | — | — |
| `AccountManager.syncArticleStatusAll()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:364-365` | @discardableResult | — |
| `AccountManager.saveAll()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:383-383` | — | — |
| `AccountManager.saveAllIfNeeded()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:389-389` | — | — |
| `AccountManager.anyAccountHasAtLeastOneFeed()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:395-395` | — | — |
| `AccountManager.anyAccountHasNetNewsWireNewsSubscription()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:405-405` | — | — |
| `AccountManager.anyAccountHasFeedWithURL(_:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:409-409` | — | — |
| `AccountManager.fetchArticles(_:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:422-422` | — | — |
| `AccountManager.fetchArticlesAsync(_:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:432-432` | — | — |
| `AccountManager.fetchArticle(accountID:articleID:)` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:449-449` | — | — |
| `AccountManager.fetchCountForStarredArticles()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:462-462` | — | — |
| `AccountManager.fetchCountForStarredArticlesAsync()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:471-471` | — | — |
| `AccountManager.fetchCountForTodayArticlesAsync()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:480-480` | — | — |
| `AccountManager.fetchUnreadCountForTodayAsync()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:489-489` | — | — |
| `AccountManager.vacuumAccountDatabases()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:500-500` | — | — |
| `AccountManager.emptyCaches()` | func | public | `Modules/Account/Sources/Account/AccountManager.swift:509-509` | — | — |
| `ArticleFetcher` | protocol | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:13-13` | @MainActor | — |
| `Feed.fetchArticles()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:22-22` | — | — |
| `Feed.fetchArticlesAsync()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:26-26` | — | — |
| `Feed.fetchUnreadArticles()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:34-34` | — | — |
| `Feed.fetchUnreadArticlesAsync()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:38-38` | — | — |
| `Folder.fetchArticles()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:51-51` | — | — |
| `Folder.fetchArticlesAsync()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:59-59` | — | — |
| `Folder.fetchUnreadArticles()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:67-67` | — | — |
| `Folder.fetchUnreadArticlesAsync()` | func | public | `Modules/Account/Sources/Account/ArticleFetcher.swift:75-75` | — | — |
| `CloudKitStatsProgressHandler` | typealias | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:10-10` | — | — |
| `CloudKitStats` | struct | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:12-12` | — | — |
| `CloudKitStats.empty` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:14-14` | — | — |
| `CloudKitStats.statusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:16-16` | — | — |
| `CloudKitStats.starredStatusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:17-17` | — | — |
| `CloudKitStats.unreadStatusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:18-18` | — | — |
| `CloudKitStats.readStatusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:19-19` | — | — |
| `CloudKitStats.staleStatusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:20-20` | — | — |
| `CloudKitStats.articleCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:22-22` | — | — |
| `CloudKitStats.starredArticleCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:23-23` | — | — |
| `CloudKitStats.unreadArticleCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:24-24` | — | — |
| `CloudKitStats.readArticleCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:25-25` | — | — |
| `CloudKitStats.cleanUpPlan(syncUnreadContent:)` | func | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:27-27` | — | — |
| `CloudKitCleanUpPlan` | struct | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:36-36` | — | — |
| `CloudKitCleanUpPlan.staleStatusCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:38-38` | — | — |
| `CloudKitCleanUpPlan.readContentCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:39-39` | — | — |
| `CloudKitCleanUpPlan.unreadContentCount` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:40-40` | — | — |
| `CloudKitCleanUpPlan.totalCount` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:42-42` | — | — |
| `CloudKitCleanUpPlan.isEmpty` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:46-46` | — | — |
| `CloudKitCleanUpPhase` | enum | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:51-51` | — | — |
| `CloudKitCleanUpProgress` | struct | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:59-59` | — | — |
| `CloudKitCleanUpProgress.phase` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:61-61` | — | — |
| `CloudKitCleanUpProgress.staleStatusDeleted` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:62-62` | — | — |
| `CloudKitCleanUpProgress.readContentDeleted` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:63-63` | — | — |
| `CloudKitCleanUpProgress.unreadContentDeleted` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:64-64` | — | — |
| `CloudKitCleanUpProgress.totalDeleted` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:66-66` | — | — |
| `CloudKitStatsError` | enum | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:10-10` | — | — |
| `CloudKitStatsError.errorDescription` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:14-14` | — | — |
| `CloudKitStatsFetchStatus` | enum | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:22-22` | — | — |
| `CloudKitStatsFetchStatus.isFetching` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:30-30` | — | — |
| `CloudKitStatsFetchStatus.isCompleted` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:37-37` | — | — |
| `CloudKitStatsFetchStatus.fetchError` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:44-44` | — | — |
| `CloudKitCleanUpStatus` | enum | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:52-52` | — | — |
| `CloudKitCleanUpStatus.isCleaning` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:60-60` | — | — |
| `CloudKitCleanUpStatus.isCompleted` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:67-67` | — | — |
| `CloudKitCleanUpStatus.isCanceled` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:74-74` | — | — |
| `CloudKitCleanUpStatus.progress` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:81-81` | — | — |
| `CloudKitCleanUpStatus.isActive` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:90-90` | — | — |
| `CloudKitCleanUpStatus.cleanUpError` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:99-99` | — | — |
| `CloudKitStatsViewModel` | class | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:107-107` | @Observable, @MainActor | — |
| `CloudKitStatsViewModel.stats` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:109-109` | — | — |
| `CloudKitStatsViewModel.fetchStatus` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:115-115` | — | — |
| `CloudKitStatsViewModel.cleanUpStatus` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:121-121` | — | — |
| `CloudKitStatsViewModel.onChange` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:128-128` | — | — |
| `CloudKitStatsViewModel.cleanUpPlanIsStale` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:130-130` | — | — |
| `CloudKitStatsViewModel.cleanUpPlan` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:136-136` | — | — |
| `CloudKitStatsViewModel.canCleanUp` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:141-141` | — | — |
| `CloudKitStatsViewModel.statsText` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:145-145` | — | — |
| `CloudKitStatsViewModel.cleanUpStatsText` | var | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:158-158` | — | — |
| `CloudKitStatsViewModel.init()` | init | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:173-173` | — | — |
| `CloudKitStatsViewModel.fetch()` | func | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:176-176` | — | — |
| `CloudKitStatsViewModel.cancelFetch()` | func | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:214-214` | — | — |
| `CloudKitStatsViewModel.cancelCleanUp()` | func | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:221-221` | — | — |
| `CloudKitStatsViewModel.cleanUp()` | func | public | `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:230-230` | — | — |
| `CloudKitWebDocumentation` | struct | public | `Modules/Account/Sources/Account/CloudKit/CloudKitWebDocumentation.swift:10-10` | — | — |
| `CloudKitWebDocumentation.limitationsAndSolutionsText` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitWebDocumentation.swift:11-11` | — | — |
| `CloudKitWebDocumentation.limitationsAndSolutionsURL` | let | public | `Modules/Account/Sources/Account/CloudKit/CloudKitWebDocumentation.swift:12-12` | — | — |
| `CombinedRefreshProgress` | class | public | `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:15-15` | @MainActor | — |
| `CombinedRefreshProgress.shared` | let | public | `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:16-16` | — | — |
| `CombinedRefreshProgress.progressInfo` | var | public | `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:18-18` | — | — |
| `CombinedRefreshProgress.isComplete` | var | public | `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:26-26` | — | — |
| `Notification.Name.ChildrenDidChange` | let | public | `Modules/Account/Sources/Account/Container.swift:14-14` | — | — |
| `Container` | protocol | public | `Modules/Account/Sources/Account/Container.swift:17-17` | @MainActor | — |
| `Container.hasAtLeastOneFeed()` | func | public | `Modules/Account/Sources/Account/Container.swift:48-48` | — | — |
| `Container.hasChildFolder(with:)` | func | public | `Modules/Account/Sources/Account/Container.swift:52-52` | @MainActor | — |
| `Container.childFolder(with:)` | func | public | `Modules/Account/Sources/Account/Container.swift:56-56` | @MainActor | — |
| `Container.objectIsChild(_:)` | func | public | `Modules/Account/Sources/Account/Container.swift:68-68` | — | — |
| `Container.flattenedFeeds()` | func | public | `Modules/Account/Sources/Account/Container.swift:78-78` | — | — |
| `Container.hasFeed(with:)` | func | public | `Modules/Account/Sources/Account/Container.swift:89-89` | — | — |
| `Container.hasFeed(withURL:)` | func | public | `Modules/Account/Sources/Account/Container.swift:93-93` | — | — |
| `Container.has(_:)` | func | public | `Modules/Account/Sources/Account/Container.swift:97-97` | — | — |
| `Container.existingFeed(withFeedID:)` | func | public | `Modules/Account/Sources/Account/Container.swift:101-101` | — | — |
| `Container.existingFeed(withURL:)` | func | public | `Modules/Account/Sources/Account/Container.swift:110-110` | — | — |
| `Container.existingFeed(withExternalID:)` | func | public | `Modules/Account/Sources/Account/Container.swift:119-119` | — | — |
| `Container.existingFolder(with:)` | func | public | `Modules/Account/Sources/Account/Container.swift:128-128` | @MainActor | — |
| `Container.existingFolder(withID:)` | func | public | `Modules/Account/Sources/Account/Container.swift:144-144` | — | — |
| `Container.postChildrenDidChangeNotification()` | func | public | `Modules/Account/Sources/Account/Container.swift:160-160` | — | — |
| `ContainerIdentifiable` | protocol | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:11-11` | @MainActor | — |
| `ContainerIdentifier` | enum | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:15-15` | — | — |
| `ContainerIdentifier.userInfo` | var | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:20-20` | — | — |
| `ContainerIdentifier.init(userInfo:)` | init | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:40-40` | — | — |
| `ContainerIdentifier.encode(to:)` | func | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:66-66` | — | — |
| `ContainerIdentifier.init(from:)` | init | public | `Modules/Account/Sources/Account/ContainerIdentifier.swift:84-84` | — | — |
| `ContainerPath` | struct | public | `Modules/Account/Sources/Account/ContainerPath.swift:15-15` | — | — |
| `ContainerPath.init(account:folders:)` | init | public | `Modules/Account/Sources/Account/ContainerPath.swift:24-24` | @MainActor | — |
| `ContainerPath.resolveContainer()` | func | public | `Modules/Account/Sources/Account/ContainerPath.swift:32-32` | @MainActor | — |
| `Notification.Name.feedSettingDidChange` | let | public | `Modules/Account/Sources/Account/DataExtensions.swift:14-14` | — | — |
| `Feed.SettingUserInfoKey` | let | public | `Modules/Account/Sources/Account/DataExtensions.swift:18-18` | — | — |
| `Feed.SettingKey` | enum | public | `Modules/Account/Sources/Account/DataExtensions.swift:20-20` | — | — |
| `Article.account` | var | public | `Modules/Account/Sources/Account/DataExtensions.swift:57-57` | @MainActor | — |
| `Article.feed` | var | public | `Modules/Account/Sources/Account/DataExtensions.swift:61-61` | @MainActor | — |
| `Feed` | class | public | `Modules/Account/Sources/Account/Feed.swift:14-14` | @MainActor | — |
| `Feed.feedID` | let | public | `Modules/Account/Sources/Account/Feed.swift:15-15` | — | — |
| `Feed.accountID` | let | public | `Modules/Account/Sources/Account/Feed.swift:16-16` | — | — |
| `Feed.url` | let | public | `Modules/Account/Sources/Account/Feed.swift:17-17` | — | — |
| `Feed.sidebarItemID` | let | public | `Modules/Account/Sources/Account/Feed.swift:18-18` | — | — |
| `Feed.account` | var | public | `Modules/Account/Sources/Account/Feed.swift:20-20` | — | — |
| `Feed.defaultReadFilterType` | var | public | `Modules/Account/Sources/Account/Feed.swift:22-22` | — | — |
| `Feed.homePageURL` | var | public | `Modules/Account/Sources/Account/Feed.swift:26-26` | — | — |
| `Feed.iconURL` | var | public | `Modules/Account/Sources/Account/Feed.swift:43-43` | — | — |
| `Feed.faviconURL` | var | public | `Modules/Account/Sources/Account/Feed.swift:56-56` | — | — |
| `Feed.name` | var | public | `Modules/Account/Sources/Account/Feed.swift:65-65` | @MainActor | — |
| `Feed.authors` | var | public | `Modules/Account/Sources/Account/Feed.swift:73-73` | — | — |
| `Feed.editedName` | var | public | `Modules/Account/Sources/Account/Feed.swift:82-82` | @MainActor | — |
| `Feed.conditionalGetInfo` | var | public | `Modules/Account/Sources/Account/Feed.swift:102-102` | — | — |
| `Feed.conditionalGetInfoDate` | var | public | `Modules/Account/Sources/Account/Feed.swift:111-111` | — | — |
| `Feed.cacheControlInfo` | var | public | `Modules/Account/Sources/Account/Feed.swift:120-120` | — | — |
| `Feed.contentHash` | var | public | `Modules/Account/Sources/Account/Feed.swift:129-129` | — | — |
| `Feed.newArticleNotificationsEnabled` | var | public | `Modules/Account/Sources/Account/Feed.swift:138-138` | — | — |
| `Feed.readerViewAlwaysEnabled` | var | public | `Modules/Account/Sources/Account/Feed.swift:147-147` | — | — |
| `Feed.externalID` | var | public | `Modules/Account/Sources/Account/Feed.swift:156-156` | — | — |
| `Feed.folderRelationship` | var | public | `Modules/Account/Sources/Account/Feed.swift:166-166` | — | — |
| `Feed.lastCheckDate` | var | public | `Modules/Account/Sources/Account/Feed.swift:177-177` | — | — |
| `Feed.lastResponseCode` | var | public | `Modules/Account/Sources/Account/Feed.swift:187-187` | — | — |
| `Feed.nameForDisplay` | var | public | `Modules/Account/Sources/Account/Feed.swift:198-198` | — | — |
| `Feed.rename(to:completion:)` | func | public | `Modules/Account/Sources/Account/Feed.swift:210-210` | — | — |
| `Feed.unreadCount` | var | public | `Modules/Account/Sources/Account/Feed.swift:226-226` | — | — |
| `Feed.notificationDisplayName` | var | public | `Modules/Account/Sources/Account/Feed.swift:240-240` | — | — |
| `Feed.dropConditionalGetInfo()` | func | public | `Modules/Account/Sources/Account/Feed.swift:275-275` | — | — |
| `Feed.hash(into:)` | func | public | `Modules/Account/Sources/Account/Feed.swift:282-282` | — | — |
| `Feed.==(lhs:rhs:)` | func | public | `Modules/Account/Sources/Account/Feed.swift:289-289` | — | — |
| `Feed.OPMLString(indentLevel:allowCustomAttributes:)` | func | public | `Modules/Account/Sources/Account/Feed.swift:298-298` | — | — |
| `FeedbinAccountDelegateError` | enum | public | `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:22-22` | — | — |
| `FeedbinDate.formatter` | let | public | `Modules/Account/Sources/Account/Feedbin/FeedbinDate.swift:12-12` | — | — |
| `FeedbinEntryJSONFeed.init(from:)` | init | public | `Modules/Account/Sources/Account/Feedbin/FeedbinEntry.swift:59-59` | — | — |
| `FeedbinSubscription.hash(into:)` | func | public | `Modules/Account/Sources/Account/Feedbin/FeedbinSubscription.swift:30-30` | — | — |
| `FeedlyAPICallerDelegate` | protocol | internal | `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:14-14` | @MainActor | — |
| `FeedlyOAuthAccessTokenResponse` | struct | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:15-15` | — | — |
| `FeedlyOAuthAccessTokenResponse.id` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:18-18` | — | — |
| `FeedlyOAuthAccessTokenResponse.accessToken` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:21-21` | — | — |
| `FeedlyOAuthAccessTokenResponse.tokenType` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:22-22` | — | — |
| `FeedlyOAuthAccessTokenResponse.expiresIn` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:23-23` | — | — |
| `FeedlyOAuthAccessTokenResponse.refreshToken` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:24-24` | — | — |
| `FeedlyOAuthAccessTokenResponse.scope` | let | public | `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:28-28` | — | — |
| `FeedlyResourceID` | protocol | internal | `Modules/Account/Sources/Account/Feedly/FeedlyModel.swift:322-322` | — | — |
| `OAuthAccountAuthorizationOperationDelegate` | protocol | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:15-15` | @MainActor | — |
| `OAuthAccountAuthorizationOperationError` | enum | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:20-20` | — | — |
| `OAuthAccountAuthorizationOperationError.errorDescription` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:24-24` | — | — |
| `PresentationAnchorProvider.presentationAnchor(for:)` | func | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:64-64` | — | — |
| `OAuthAccountAuthorizationOperation` | class | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:72-72` | — | — |
| `OAuthAccountAuthorizationOperation.presentationAnchor` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:73-73` | — | — |
| `OAuthAccountAuthorizationOperation.delegate` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:82-82` | — | — |
| `OAuthAccountAuthorizationOperation.init(accountType:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:108-108` | — | — |
| `OAuthAccountAuthorizationOperation.run()` | func | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:114-114` | — | — |
| `OAuthAccountAuthorizationOperation.noteDidComplete()` | func | public | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:140-140` | — | — |
| `OAuthAuthorizationClient` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:15-15` | — | — |
| `OAuthAuthorizationClient.id` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:16-16` | — | — |
| `OAuthAuthorizationClient.redirectURI` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:17-17` | — | — |
| `OAuthAuthorizationClient.secret` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:18-18` | — | — |
| `OAuthAuthorizationClient.init(id:redirectURI:secret:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:20-20` | — | — |
| `OAuthAuthorizationRequest` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:29-29` | — | — |
| `OAuthAuthorizationRequest.responseType` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:30-30` | — | — |
| `OAuthAuthorizationRequest.clientID` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:31-31` | — | — |
| `OAuthAuthorizationRequest.redirectURI` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:32-32` | — | — |
| `OAuthAuthorizationRequest.scope` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:33-33` | — | — |
| `OAuthAuthorizationRequest.state` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:34-34` | — | — |
| `OAuthAuthorizationRequest.init(clientID:redirectURI:scope:state:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:36-36` | — | — |
| `OAuthAuthorizationRequest.queryItems` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:43-43` | — | — |
| `OAuthAuthorizationResponse` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:59-59` | — | — |
| `OAuthAuthorizationResponse.code` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:60-60` | — | — |
| `OAuthAuthorizationResponse.state` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:61-61` | — | — |
| `OAuthAuthorizationResponse.init(url:client:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:81-81` | — | — |
| `OAuthAccessTokenRequest` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:112-112` | — | — |
| `OAuthAccessTokenRequest.grantType` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:113-113` | — | — |
| `OAuthAccessTokenRequest.code` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:114-114` | — | — |
| `OAuthAccessTokenRequest.redirectURI` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:115-115` | — | — |
| `OAuthAccessTokenRequest.state` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:116-116` | — | — |
| `OAuthAccessTokenRequest.clientID` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:117-117` | — | — |
| `OAuthAccessTokenRequest.clientSecret` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:120-120` | — | — |
| `OAuthAccessTokenRequest.scope` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:121-121` | — | — |
| `OAuthAccessTokenRequest.init(authorizationResponse:scope:client:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:123-123` | — | — |
| `OAuthRefreshAccessTokenRequest` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:135-135` | — | — |
| `OAuthRefreshAccessTokenRequest.grantType` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:136-136` | — | — |
| `OAuthRefreshAccessTokenRequest.refreshToken` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:137-137` | — | — |
| `OAuthRefreshAccessTokenRequest.scope` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:138-138` | — | — |
| `OAuthRefreshAccessTokenRequest.clientID` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:141-141` | — | — |
| `OAuthRefreshAccessTokenRequest.clientSecret` | var | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:142-142` | — | — |
| `OAuthRefreshAccessTokenRequest.init(refreshToken:scope:client:)` | init | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:144-144` | — | — |
| `OAuthAccessTokenResponse` | protocol | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:156-156` | — | — |
| `OAuthAuthorizationGrant` | struct | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:165-165` | — | — |
| `OAuthAuthorizationGrant.accessToken` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:166-166` | — | — |
| `OAuthAuthorizationGrant.refreshToken` | let | public | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:167-167` | — | — |
| `OAuthAuthorizationGranting` | protocol | internal | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:172-172` | — | — |
| `Folder` | class | public | `Modules/Account/Sources/Account/Folder.swift:13-13` | — | — |
| `Folder.accountID` | let | public | `Modules/Account/Sources/Account/Folder.swift:14-14` | — | — |
| `Folder.account` | var | public | `Modules/Account/Sources/Account/Folder.swift:15-15` | — | — |
| `Folder.defaultReadFilterType` | var | public | `Modules/Account/Sources/Account/Folder.swift:17-17` | — | — |
| `Folder.containerID` | var | public | `Modules/Account/Sources/Account/Folder.swift:21-21` | — | — |
| `Folder.sidebarItemID` | var | public | `Modules/Account/Sources/Account/Folder.swift:25-25` | — | — |
| `Folder.topLevelFeeds` | var | public | `Modules/Account/Sources/Account/Folder.swift:29-29` | — | — |
| `Folder.folders` | var | public | `Modules/Account/Sources/Account/Folder.swift:30-30` | — | — |
| `Folder.name` | var | public | `Modules/Account/Sources/Account/Folder.swift:32-32` | — | — |
| `Folder.folderID` | let | public | `Modules/Account/Sources/Account/Folder.swift:39-39` | — | — |
| `Folder.externalID` | var | public | `Modules/Account/Sources/Account/Folder.swift:40-40` | — | — |
| `Folder.nameForDisplay` | var | public | `Modules/Account/Sources/Account/Folder.swift:45-45` | — | — |
| `Folder.unreadCount` | var | public | `Modules/Account/Sources/Account/Folder.swift:51-51` | — | — |
| `Folder.rename(to:completion:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:61-61` | — | — |
| `Folder.flattenedFeeds()` | func | public | `Modules/Account/Sources/Account/Folder.swift:114-114` | — | — |
| `Folder.objectIsChild(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:119-119` | — | — |
| `Folder.addFeedToTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:127-127` | — | — |
| `Folder.addFeeds(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:132-132` | — | — |
| `Folder.removeFeedFromTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:140-140` | — | — |
| `Folder.removeFeedsFromTreeAtTopLevel(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:145-145` | — | — |
| `Folder.replaceTopLevelFeeds(_:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:154-154` | — | — |
| `Folder.hash(into:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:161-161` | — | — |
| `Folder.==(lhs:rhs:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:167-167` | — | — |
| `Folder.OPMLString(indentLevel:allowCustomAttributes:)` | func | public | `Modules/Account/Sources/Account/Folder.swift:185-185` | — | — |
| `LocalAccountRefresherDelegate` | protocol | internal | `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:19-19` | @MainActor | — |
| `LocalAccountRefresher.refreshFeeds(_:)` | func | public | `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:78-78` | @MainActor | — |
| `LocalAccountRefresher.suspend()` | func | public | `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:167-167` | @MainActor | — |
| `LocalAccountRefresher.resume()` | func | public | `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:172-172` | @MainActor | — |
| `ReaderAPIAccountDelegateError` | enum | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:21-21` | — | — |
| `ReaderAPIAccountDelegateError.errorDescription` | var | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:28-28` | — | — |
| `ReaderAPIAccountDelegate.sendArticleStatus()` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:215-215` | — | — |
| `ReaderAPICaller.validateCredentials(endpoint:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:106-106` | — | — |
| `ReaderAPICaller.retrieveTags()` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:193-193` | @MainActor | — |
| `ReaderAPICaller.renameTag(oldName:newName:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:220-220` | @MainActor | — |
| `ReaderAPICaller.deleteTag(folderExternalID:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:244-244` | @MainActor | — |
| `ReaderAPICaller.retrieveSubscriptions()` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:261-261` | @MainActor | — |
| `ReaderAPICaller.createSubscription(url:name:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:292-292` | @MainActor | — |
| `ReaderAPICaller.renameSubscription(subscriptionID:newName:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:341-341` | — | — |
| `ReaderAPICaller.deleteSubscription(subscriptionID:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:346-346` | @MainActor | — |
| `ReaderAPICaller.createTagging(subscriptionID:tagName:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:363-363` | — | — |
| `ReaderAPICaller.deleteTagging(subscriptionID:tagName:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:368-368` | — | — |
| `ReaderAPICaller.moveSubscription(subscriptionID:sourceTag:destinationTag:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:373-373` | — | — |
| `ReaderAPICaller.retrieveEntries(articleIDs:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:420-420` | @MainActor | — |
| `ReaderAPICaller.retrieveItemIDs(type:feedID:pageHandler:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:453-453` | @MainActor | — |
| `ReaderAPICaller.createUnreadEntries(entries:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:577-577` | — | — |
| `ReaderAPICaller.deleteUnreadEntries(entries:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:582-582` | — | — |
| `ReaderAPICaller.createStarredEntries(entries:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:587-587` | — | — |
| `ReaderAPICaller.deleteStarredEntries(entries:)` | func | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:592-592` | — | — |
| `ReaderAPIVariant` | enum | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIVariant.swift:10-10` | — | — |
| `ReaderAPIVariant.host` | var | public | `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIVariant.swift:17-17` | — | — |
| `ReadFilterType` | enum | public | `Modules/Account/Sources/Account/SidebarItem.swift:12-12` | — | — |
| `SidebarItem` | protocol | public | `Modules/Account/Sources/Account/SidebarItem.swift:18-18` | @MainActor | — |
| `SidebarItem.readFiltered(readFilterEnabledTable:)` | func | public | `Modules/Account/Sources/Account/SidebarItem.swift:25-25` | — | — |
| `SidebarItemIdentifiable` | protocol | public | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:11-11` | @MainActor | — |
| `SidebarItemIdentifier` | enum | public | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:15-15` | — | — |
| `SidebarItemIdentifier.description` | var | public | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:47-47` | — | — |
| `SidebarItemIdentifier.userInfo` | var | public | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:58-58` | — | — |
| `SidebarItemIdentifier.init(userInfo:)` | init | public | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:75-75` | — | — |
| `SingleArticleFetcher` | struct | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:13-13` | — | — |
| `SingleArticleFetcher.init(account:articleID:)` | init | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:18-18` | — | — |
| `SingleArticleFetcher.fetchArticles()` | func | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:23-23` | — | — |
| `SingleArticleFetcher.fetchArticlesAsync()` | func | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:27-27` | — | — |
| `SingleArticleFetcher.fetchUnreadArticles()` | func | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:31-31` | — | — |
| `SingleArticleFetcher.fetchUnreadArticlesAsync()` | func | public | `Modules/Account/Sources/Account/SingleArticleFetcher.swift:35-35` | — | — |
| `URLRequest.init(url:credentials:conditionalGet:)` | init | public | `Modules/Account/Sources/Account/URLRequest+Account.swift:16-16` | — | — |
| `Notification.Name.UnreadCountDidInitialize` | let | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:12-12` | — | — |
| `Notification.Name.UnreadCountDidChange` | let | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:13-13` | — | — |
| `UnreadCountProvider` | protocol | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:16-16` | @MainActor | — |
| `UnreadCountProvider.postUnreadCountDidInitializeNotification()` | func | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:25-25` | — | — |
| `UnreadCountProvider.postUnreadCountDidChangeNotification()` | func | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:29-29` | — | — |
| `UnreadCountProvider.calculateUnreadCount(_:)` | func | public | `Modules/Account/Sources/Account/UnreadCountProvider.swift:33-33` | — | — |
| `Activity` | class | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:11-11` | @MainActor | — |
| `Activity.id` | let | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:13-13` | — | — |
| `Activity.owner` | let | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:14-14` | — | — |
| `Activity.kind` | let | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:15-15` | — | — |
| `Activity.detail` | let | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:16-16` | — | — |
| `Activity.state` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:18-18` | — | — |
| `Activity.startDate` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:19-19` | — | — |
| `Activity.endDate` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:20-20` | — | — |
| `Activity.error` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:21-21` | — | — |
| `Activity.completionMessage` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:22-22` | — | — |
| `Activity.returnedFromCache` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:23-23` | — | — |
| `Activity.durationIsSignificant` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:26-26` | — | — |
| `Activity.init(id:owner:kind:detail:)` | init | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:28-28` | — | — |
| `Activity.formattedDuration` | var | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:64-64` | — | — |
| `Activity.hash(into:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:88-88` | — | — |
| `Activity.==(lhs:rhs:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:92-92` | — | — |
| `ActivityKind` | enum | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityKind.swift:12-12` | — | — |
| `ActivityKind.simpleDisplayName` | var | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityKind.swift:69-69` | — | — |
| `ActivityKind.displayName(detail:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityKind.swift:134-134` | — | — |
| `Notification.Name.activityDidChange` | let | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:12-12` | — | — |
| `ActivityLog` | class | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:20-20` | @MainActor | — |
| `ActivityLog.shared` | let | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:22-22` | — | — |
| `ActivityLog.pendingActivities` | var | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:25-25` | — | — |
| `ActivityLog.runningActivities` | var | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:28-28` | — | — |
| `ActivityLog.completedActivities` | var | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:31-31` | — | — |
| `ActivityLog.completedActivitiesLimit` | let | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:34-34` | — | — |
| `ActivityLog.init()` | init | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:39-39` | — | — |
| `ActivityLog.nextTaskNumberString()` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:43-43` | — | — |
| `ActivityLog.createActivity(owner:kind:detail:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:51-52` | @discardableResult | — |
| `ActivityLog.logCompletedActivity(owner:kind:detail:message:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:67-67` | — | — |
| `ActivityLog.logActivity(owner:kind:detail:successMessage:durationIsSignificant:_:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:75-76` | @discardableResult | — |
| `ActivityLog.logActivity(owner:kind:detail:successMessage:durationIsSignificant:_:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:97-98` | @discardableResult | — |
| `ActivityLog.didStart(_:kind:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:120-120` | — | — |
| `ActivityLog.startIfNeeded(_:kind:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:134-134` | — | — |
| `ActivityLog.didComplete(_:kind:message:durationIsSignificant:returnedFromCache:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:152-152` | — | — |
| `ActivityLog.didFail(_:kind:error:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:168-168` | — | — |
| `ActivityLog.didStart(id:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:182-182` | — | — |
| `ActivityLog.didComplete(id:message:durationIsSignificant:returnedFromCache:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:196-196` | — | — |
| `ActivityLog.didFail(id:error:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:211-211` | — | — |
| `ActivityLog.pendingActivities(for:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:226-226` | — | — |
| `ActivityLog.runningActivities(for:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:230-230` | — | — |
| `ActivityLog.completedActivities(for:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:234-234` | — | — |
| `ActivityLog.dataSizeMessage(_:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityLogDataSize.swift:13-13` | — | — |
| `ActivityOwner` | enum | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityOwner.swift:10-10` | — | — |
| `ActivityOwner.displayName` | var | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityOwner.swift:20-20` | — | — |
| `ActivityOwner.==(lhs:rhs:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityOwner.swift:42-42` | — | — |
| `ActivityOwner.hash(into:)` | func | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityOwner.swift:58-58` | — | — |
| `ActivityState` | enum | public | `Modules/ActivityLog/Sources/ActivityLog/ActivityState.swift:9-9` | — | — |
| `ArticleSetBlock` | typealias | public | `Modules/Articles/Sources/Articles/Article.swift:12-12` | — | — |
| `Article` | class | public | `Modules/Articles/Sources/Articles/Article.swift:14-14` | — | — |
| `Article.articleID` | let | public | `Modules/Articles/Sources/Articles/Article.swift:15-15` | — | — |
| `Article.accountID` | let | public | `Modules/Articles/Sources/Articles/Article.swift:16-16` | — | — |
| `Article.feedID` | let | public | `Modules/Articles/Sources/Articles/Article.swift:17-17` | — | — |
| `Article.uniqueID` | let | public | `Modules/Articles/Sources/Articles/Article.swift:18-18` | — | — |
| `Article.title` | let | public | `Modules/Articles/Sources/Articles/Article.swift:19-19` | — | — |
| `Article.contentHTML` | let | public | `Modules/Articles/Sources/Articles/Article.swift:20-20` | — | — |
| `Article.contentText` | let | public | `Modules/Articles/Sources/Articles/Article.swift:21-21` | — | — |
| `Article.markdown` | let | public | `Modules/Articles/Sources/Articles/Article.swift:22-22` | — | — |
| `Article.rawLink` | let | public | `Modules/Articles/Sources/Articles/Article.swift:23-23` | — | — |
| `Article.rawExternalLink` | let | public | `Modules/Articles/Sources/Articles/Article.swift:24-24` | — | — |
| `Article.summary` | let | public | `Modules/Articles/Sources/Articles/Article.swift:25-25` | — | — |
| `Article.rawImageLink` | let | public | `Modules/Articles/Sources/Articles/Article.swift:26-26` | — | — |
| `Article.datePublished` | let | public | `Modules/Articles/Sources/Articles/Article.swift:27-27` | — | — |
| `Article.dateModified` | let | public | `Modules/Articles/Sources/Articles/Article.swift:28-28` | — | — |
| `Article.authors` | let | public | `Modules/Articles/Sources/Articles/Article.swift:29-29` | — | — |
| `Article.status` | let | public | `Modules/Articles/Sources/Articles/Article.swift:30-30` | — | — |
| `Article.init(accountID:articleID:feedID:uniqueID:title:contentHTML:contentText:markdown:url:externalURL:summary:imageURL:datePublished:dateModified:authors:status:)` | init | public | `Modules/Articles/Sources/Articles/Article.swift:32-32` | — | — |
| `Article.calculatedArticleID(feedID:uniqueID:)` | func | public | `Modules/Articles/Sources/Articles/Article.swift:56-56` | — | — |
| `Article.hash(into:)` | func | public | `Modules/Articles/Sources/Articles/Article.swift:62-62` | — | — |
| `Article.==(lhs:rhs:)` | func | public | `Modules/Articles/Sources/Articles/Article.swift:68-68` | — | — |
| `Set.articleIDs()` | func | public | `Modules/Articles/Sources/Articles/Article.swift:75-75` | — | — |
| `Set.unreadArticles()` | func | public | `Modules/Articles/Sources/Articles/Article.swift:79-79` | — | — |
| `Set.contains(accountID:articleID:)` | func | public | `Modules/Articles/Sources/Articles/Article.swift:84-84` | — | — |
| `Array.articleIDs()` | func | public | `Modules/Articles/Sources/Articles/Article.swift:91-91` | — | — |
| `ArticleStatus` | class | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:12-12` | — | — |
| `ArticleStatus.staleIntervalInSeconds` | let | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:16-16` | — | — |
| `ArticleStatus.Key` | enum | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:17-17` | — | — |
| `ArticleStatus.articleID` | let | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:22-22` | — | — |
| `ArticleStatus.dateArrived` | let | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:23-23` | — | — |
| `ArticleStatus.read` | var | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:32-32` | — | — |
| `ArticleStatus.starred` | var | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:41-41` | — | — |
| `ArticleStatus.init(articleID:read:starred:dateArrived:)` | init | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:50-50` | — | — |
| `ArticleStatus.init(articleID:read:dateArrived:)` | init | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:56-56` | — | — |
| `ArticleStatus.boolStatus(forKey:)` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:60-60` | — | — |
| `ArticleStatus.setBoolStatus(_:forKey:)` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:69-69` | — | — |
| `ArticleStatus.hash(into:)` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:80-80` | — | — |
| `ArticleStatus.==(lhs:rhs:)` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:86-86` | — | — |
| `Set.articleIDs()` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:93-93` | — | — |
| `Array.articleIDs()` | func | public | `Modules/Articles/Sources/Articles/ArticleStatus.swift:100-100` | — | — |
| `Author` | struct | public | `Modules/Articles/Sources/Articles/Author.swift:12-12` | — | — |
| `Author.authorID` | let | public | `Modules/Articles/Sources/Articles/Author.swift:13-13` | — | — |
| `Author.name` | let | public | `Modules/Articles/Sources/Articles/Author.swift:14-14` | — | — |
| `Author.url` | let | public | `Modules/Articles/Sources/Articles/Author.swift:15-15` | — | — |
| `Author.avatarURL` | let | public | `Modules/Articles/Sources/Articles/Author.swift:16-16` | — | — |
| `Author.emailAddress` | let | public | `Modules/Articles/Sources/Articles/Author.swift:17-17` | — | — |
| `Author.init(authorID:name:url:avatarURL:emailAddress:)` | init | public | `Modules/Articles/Sources/Articles/Author.swift:19-19` | — | — |
| `Author.authorsWithJSON(_:)` | func | public | `Modules/Articles/Sources/Articles/Author.swift:39-39` | — | — |
| `Author.hash(into:)` | func | public | `Modules/Articles/Sources/Articles/Author.swift:53-53` | — | — |
| `Author.==(lhs:rhs:)` | func | public | `Modules/Articles/Sources/Articles/Author.swift:59-59` | — | — |
| `Set.json()` | func | public | `Modules/Articles/Sources/Articles/Author.swift:68-68` | — | — |
| `AuthorCache` | class | public | `Modules/Articles/Sources/Articles/AuthorCache.swift:14-14` | — | — |
| `AuthorCache.shared` | let | public | `Modules/Articles/Sources/Articles/AuthorCache.swift:16-16` | — | — |
| `AuthorCache.add(_:)` | func | public | `Modules/Articles/Sources/Articles/AuthorCache.swift:26-26` | — | — |
| `AuthorCache.clear()` | func | public | `Modules/Articles/Sources/Articles/AuthorCache.swift:38-38` | — | — |
| `UnreadCountDictionary` | typealias | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:19-19` | — | — |
| `ArticleChanges` | struct | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:21-21` | — | — |
| `ArticleChanges.new` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:22-22` | — | — |
| `ArticleChanges.updated` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:23-23` | — | — |
| `ArticleChanges.deleted` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:24-24` | — | — |
| `ArticleChanges.init()` | init | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:26-26` | — | — |
| `ArticleChanges.init(new:updated:deleted:)` | init | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:32-32` | — | — |
| `ArticleCounts` | struct | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:40-40` | — | — |
| `ArticleCounts.totalCount` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:41-41` | — | — |
| `ArticleCounts.unreadCount` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:42-42` | — | — |
| `ArticleCounts.starredCount` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:43-43` | — | — |
| `ArticleCounts.statusesCount` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:44-44` | — | — |
| `ArticlesDatabase` | class | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:47-47` | @MainActor | — |
| `ArticlesDatabase.RetentionStyle` | enum | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:48-48` | — | — |
| `ArticlesDatabase.databasePath` | let | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:53-53` | — | — |
| `ArticlesDatabase.init(databaseFilePath:accountID:retentionStyle:)` | init | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:63-63` | — | — |
| `ArticlesDatabase.vacuum()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:105-105` | — | — |
| `ArticlesDatabase.repairStatuses()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:113-113` | — | — |
| `ArticlesDatabase.fetchArticles(feedID:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:121-121` | — | — |
| `ArticlesDatabase.fetchArticles(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:126-126` | — | — |
| `ArticlesDatabase.fetchArticles(articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:131-131` | — | — |
| `ArticlesDatabase.fetchUnreadArticles(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:136-136` | — | — |
| `ArticlesDatabase.fetchTodayArticles(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:141-141` | — | — |
| `ArticlesDatabase.fetchStarredArticles(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:146-146` | — | — |
| `ArticlesDatabase.fetchStarredArticlesCount(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:151-151` | — | — |
| `ArticlesDatabase.fetchArticleCountsAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:157-157` | — | — |
| `ArticlesDatabase.fetchArticlesMatching(searchString:feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:166-166` | — | — |
| `ArticlesDatabase.fetchArticlesMatchingWithArticleIDs(searchString:articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:171-171` | — | — |
| `ArticlesDatabase.fetchLastUpdateDates()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:177-177` | — | — |
| `ArticlesDatabase.fetchArticlesAsync(feedID:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:188-188` | — | — |
| `ArticlesDatabase.fetchArticlesAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:196-196` | — | — |
| `ArticlesDatabase.fetchArticlesAsync(articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:204-204` | — | — |
| `ArticlesDatabase.fetchUnreadArticlesAsync(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:212-212` | — | — |
| `ArticlesDatabase.fetchTodayArticlesAsync(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:220-220` | — | — |
| `ArticlesDatabase.fetchedStarredArticlesAsync(feedIDs:limit:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:228-228` | — | — |
| `ArticlesDatabase.fetchArticlesMatchingAsync(searchString:feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:236-236` | — | — |
| `ArticlesDatabase.fetchArticlesMatchingWithArticleIDsAsync(searchString:articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:244-244` | — | — |
| `ArticlesDatabase.fetchAllUnreadCountsAsync()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:255-255` | — | — |
| `ArticlesDatabase.fetchUnreadCountAsync(feedID:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:264-264` | — | — |
| `ArticlesDatabase.fetchUnreadCountsAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:278-278` | — | — |
| `ArticlesDatabase.fetchUnreadCountForTodayAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:286-286` | — | — |
| `ArticlesDatabase.fetchUnreadCountForStarredArticlesAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:294-294` | — | — |
| `ArticlesDatabase.fetchTodayArticlesCountAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:302-302` | — | — |
| `ArticlesDatabase.fetchStarredArticlesCountAsync(feedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:310-310` | — | — |
| `ArticlesDatabase.updateAsync(parsedItems:feedID:deleteOlder:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:321-321` | — | — |
| `ArticlesDatabase.updateAsync(feedIDsAndItems:defaultRead:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:330-330` | — | — |
| `ArticlesDatabase.deleteAsync(articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:339-339` | — | — |
| `ArticlesDatabase.fetchUnreadArticleIDsAsync()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:350-350` | — | — |
| `ArticlesDatabase.fetchStarredArticleIDsAsync()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:358-358` | — | — |
| `ArticlesDatabase.fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDateAsync()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:367-367` | — | — |
| `ArticlesDatabase.markAsync(articleIDs:statusKey:flag:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:378-378` | — | — |
| `ArticlesDatabase.markAndFetchNewAsync(articleIDs:statusKey:flag:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:386-386` | — | — |
| `ArticlesDatabase.createStatusesIfNeededAsync(articleIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:396-396` | — | — |
| `ArticlesDatabase.emptyCaches()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:408-408` | — | — |
| `ArticlesDatabase.cleanupDatabaseAtStartup(subscribedToFeedIDs:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:420-420` | — | — |
| `ArticlesTable.delete(articleIDs:completion:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:345-345` | — | — |
| `Author.authorsWithParsedAuthors(_:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Author+Database.swift:19-19` | — | — |
| `FetchAllUnreadCountsOperation` | class | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:15-15` | @MainActor | — |
| `FetchAllUnreadCountsOperation.run()` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:37-37` | — | — |
| `ArticleSearchInfo.hash(into:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:71-71` | — | — |
| `SearchTable.SearchInfo.hash(into:)` | func | public | `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:162-162` | — | — |
| `CloudKitError` | class | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:14-14` | — | — |
| `CloudKitError.error` | let | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:16-16` | — | — |
| `CloudKitError.init(_:)` | init | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:18-18` | — | — |
| `CloudKitError.errorDescription` | var | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:22-22` | — | — |
| `cloudKitLogger` | let | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitLogger.swift:12-12` | — | — |
| `CloudKitQueryPageHandler` | typealias | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:17-17` | — | — |
| `CloudKitZoneError` | enum | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:19-19` | — | — |
| `CloudKitZoneError.errorDescription` | var | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:24-24` | — | — |
| `CloudKitZoneDelegate` | protocol | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:43-43` | — | — |
| `CloudKitRecordKey` | typealias | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:47-47` | — | — |
| `CloudKitZoneFetchPageHandler` | typealias | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:51-51` | — | — |
| `CloudKitZone` | protocol | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:53-53` | @MainActor | — |
| `CloudKitZone.qualityOfService` | var | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:83-83` | — | — |
| `CloudKitZone.changeTokenKey` | var | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:95-95` | — | — |
| `CloudKitZone.changeToken` | var | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:99-99` | — | — |
| `CloudKitZone.resetChangeToken()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:114-114` | — | — |
| `CloudKitZone.generateRecordID()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:119-119` | — | — |
| `CloudKitZone.delaySeconds(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:123-123` | — | — |
| `CloudKitZone.receiveRemoteNotification(userInfo:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:127-127` | — | — |
| `CloudKitZone.createZoneRecord(completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:142-142` | — | — |
| `CloudKitZone.subscribeToZoneChanges()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:161-161` | — | — |
| `CloudKitZone.query(_:desiredKeys:pageHandler:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:177-177` | — | — |
| `CloudKitZone.query(cursor:desiredKeys:carriedRecords:pageHandler:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:245-245` | — | — |
| `CloudKitZone.fetch(externalID:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:312-312` | — | — |
| `CloudKitZone.save(_:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:361-361` | — | — |
| `CloudKitZone.save(_:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:367-367` | — | — |
| `CloudKitZone.saveIfNew(_:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:373-373` | — | — |
| `CloudKitZone.save(_:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:450-450` | — | — |
| `CloudKitZone.delete(ckQuery:pageHandler:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:485-485` | — | — |
| `CloudKitZone.delete(cursor:carriedRecords:pageHandler:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:531-531` | — | — |
| `CloudKitZone.delete(recordID:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:574-574` | — | — |
| `CloudKitZone.delete(recordIDs:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:580-580` | — | — |
| `CloudKitZone.delete(externalID:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:586-586` | — | — |
| `CloudKitZone.delete(subscriptionID:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:598-598` | — | — |
| `CloudKitZone.modify(recordsToSave:recordIDsToDelete:completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:625-625` | — | — |
| `CloudKitZone.fetchChangesInZone(completion:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:741-741` | — | — |
| `CloudKitZone.createZoneRecord()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:862-862` | — | — |
| `CloudKitZone.query(_:desiredKeys:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:870-870` | — | — |
| `CloudKitZone.queryPaginated(_:desiredKeys:pageHandler:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:878-878` | — | — |
| `CloudKitZone.fetch(externalID:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:908-908` | — | — |
| `CloudKitZone.save(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:916-916` | — | — |
| `CloudKitZone.save(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:924-924` | — | — |
| `CloudKitZone.saveIfNew(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:932-932` | — | — |
| `CloudKitZone.save(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:940-940` | — | — |
| `CloudKitZone.subscribeToZoneChanges()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:953-953` | — | — |
| `CloudKitZone.delete(ckQuery:pageHandler:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:961-961` | — | — |
| `CloudKitZone.delete(recordID:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:969-969` | — | — |
| `CloudKitZone.delete(recordIDs:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:977-977` | — | — |
| `CloudKitZone.delete(externalID:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:985-985` | — | — |
| `CloudKitZone.delete(subscriptionID:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:993-993` | — | — |
| `CloudKitZone.modify(recordsToSave:recordIDsToDelete:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:1001-1001` | — | — |
| `CloudKitZone.fetchChangesInZone()` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:1009-1009` | — | — |
| `CloudKitZoneResult` | enum | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZoneResult.swift:12-12` | — | — |
| `CloudKitZoneResult.resolve(_:)` | func | public | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZoneResult.swift:23-23` | — | — |
| `ErrorLogDatabase` | actor | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:13-13` | — | — |
| `ErrorLogDatabase.databasePath` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:15-15` | — | — |
| `ErrorLogDatabase.init(databasePath:)` | init | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:23-23` | — | — |
| `ErrorLogDatabase.addEntry(sourceName:sourceID:operation:fileName:functionName:lineNumber:errorMessage:)` | func | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:37-37` | — | — |
| `ErrorLogDatabase.vacuum()` | func | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:41-41` | — | — |
| `ErrorLogDatabase.allEntries()` | func | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:45-45` | — | — |
| `ErrorLogEntry` | struct | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:11-11` | — | — |
| `ErrorLogEntry.id` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:13-13` | — | — |
| `ErrorLogEntry.date` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:14-14` | — | — |
| `ErrorLogEntry.sourceName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:15-15` | — | — |
| `ErrorLogEntry.sourceID` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:16-16` | — | — |
| `ErrorLogEntry.operation` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:17-17` | — | — |
| `ErrorLogEntry.fileName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:18-18` | — | — |
| `ErrorLogEntry.functionName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:19-19` | — | — |
| `ErrorLogEntry.lineNumber` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:20-20` | — | — |
| `ErrorLogEntry.errorMessage` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:21-21` | — | — |
| `ErrorLogEntry.init(id:date:sourceName:sourceID:operation:fileName:functionName:lineNumber:errorMessage:)` | init | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:23-23` | — | — |
| `Notification.Name.appDidEncounterError` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:14-14` | — | — |
| `ErrorLogUserInfoKey` | struct | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:17-17` | — | — |
| `ErrorLogUserInfoKey.sourceName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:19-19` | — | — |
| `ErrorLogUserInfoKey.sourceID` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:20-20` | — | — |
| `ErrorLogUserInfoKey.operation` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:21-21` | — | — |
| `ErrorLogUserInfoKey.fileName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:22-22` | — | — |
| `ErrorLogUserInfoKey.functionName` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:23-23` | — | — |
| `ErrorLogUserInfoKey.lineNumber` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:24-24` | — | — |
| `ErrorLogUserInfoKey.errorMessage` | let | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:25-25` | — | — |
| `ErrorLogUserInfoKey.userInfo(sourceName:sourceID:operation:errorMessage:fileName:functionName:lineNumber:)` | func | public | `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:27-27` | — | — |
| `FeedFinderError` | enum | public | `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:16-16` | — | — |
| `FeedFinderError.errorDescription` | var | public | `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:19-19` | — | — |
| `FeedFinder` | class | public | `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:27-27` | — | — |
| `FeedFinder.find(url:)` | func | public | `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:40-40` | @concurrent | — |
| `FeedFinder.downloadAndLog(_:)` | func | public | `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:97-97` | — | — |
| `FeedSpecifier` | struct | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:12-12` | — | — |
| `FeedSpecifier.Source` | enum | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:13-13` | — | — |
| `FeedSpecifier.title` | let | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:21-21` | — | — |
| `FeedSpecifier.urlString` | let | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:22-22` | — | — |
| `FeedSpecifier.source` | let | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:23-23` | — | — |
| `FeedSpecifier.orderFound` | let | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:24-24` | — | — |
| `FeedSpecifier.score` | var | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:25-25` | — | — |
| `FeedSpecifier.init(title:urlString:source:orderFound:)` | init | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:29-29` | — | — |
| `FeedSpecifier.bestFeed(in:)` | func | public | `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:63-63` | — | — |
| `HTMLMetadataDatabase` | actor | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:13-13` | — | — |
| `HTMLMetadataDatabase.shared` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:15-15` | @MainActor | — |
| `HTMLMetadataDatabase.databasePath` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:21-21` | — | — |
| `HTMLMetadataDatabase.vacuum()` | func | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:76-76` | — | — |
| `HTMLMetadataDownloader` | class | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:16-16` | — | — |
| `HTMLMetadataDownloader.shared` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:18-18` | — | — |
| `HTMLMetadataDownloader.cachedMetadata(for:)` | func | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:44-44` | — | — |
| `Notification.Name.htmlMetadataAvailable` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataNotification.swift:13-13` | — | — |
| `HTMLMetadataUserInfoKey` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataNotification.swift:16-16` | — | — |
| `HTMLMetadataUserInfoKey.record` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataNotification.swift:18-18` | — | — |
| `HTMLMetadataUserInfoKey.url` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataNotification.swift:19-19` | — | — |
| `HTMLMetadataRecord` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:11-11` | — | — |
| `HTMLMetadataRecord.url` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:13-13` | — | — |
| `HTMLMetadataRecord.favicons` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:14-14` | — | — |
| `HTMLMetadataRecord.appleTouchIcons` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:15-15` | — | — |
| `HTMLMetadataRecord.feedLinks` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:16-16` | — | — |
| `HTMLMetadataRecord.openGraphImages` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:17-17` | — | — |
| `HTMLMetadataRecord.twitterImageURL` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:18-18` | — | — |
| `HTMLMetadataRecord.init(url:metadata:)` | init | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:31-31` | — | — |
| `HTMLMetadataRecord.Favicon` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:71-71` | — | — |
| `HTMLMetadataRecord.Favicon.type` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:72-72` | — | — |
| `HTMLMetadataRecord.Favicon.urlString` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:73-73` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:76-76` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon.rel` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:77-77` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon.sizes` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:78-78` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon.width` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:79-79` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon.height` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:80-80` | — | — |
| `HTMLMetadataRecord.AppleTouchIcon.urlString` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:81-81` | — | — |
| `HTMLMetadataRecord.FeedLink` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:84-84` | — | — |
| `HTMLMetadataRecord.FeedLink.title` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:85-85` | — | — |
| `HTMLMetadataRecord.FeedLink.type` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:86-86` | — | — |
| `HTMLMetadataRecord.FeedLink.urlString` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:87-87` | — | — |
| `HTMLMetadataRecord.OpenGraphImage` | struct | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:90-90` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.url` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:91-91` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.secureURL` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:92-92` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.mimeType` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:93-93` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.width` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:94-94` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.height` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:95-95` | — | — |
| `HTMLMetadataRecord.OpenGraphImage.altText` | let | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:96-96` | — | — |
| `HTMLMetadataRecord.bestWebsiteIconURL()` | func | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:104-104` | — | — |
| `HTMLMetadataRecord.largestOpenGraphImageURL()` | func | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:114-114` | — | — |
| `HTMLMetadataRecord.largestAppleTouchIcon()` | func | public | `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:146-146` | — | — |
| `Notification.Name.AvatarDidBecomeAvailable` | let | public | `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:15-15` | — | — |
| `AuthorAvatarDownloader` | class | public | `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:18-18` | @MainActor | — |
| `AuthorAvatarDownloader.shared` | let | public | `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:19-19` | — | — |
| `AuthorAvatarDownloader.image(for:)` | func | public | `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:39-39` | — | — |
| `AuthorAvatarDownloader.cachedImage(for:)` | func | public | `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:59-59` | — | — |
| `ColorHash` | class | public | `Modules/Images/Sources/Images/ColorHash.swift:20-20` | — | — |
| `ColorHash.defaultSaturation` | let | public | `Modules/Images/Sources/Images/ColorHash.swift:22-22` | — | — |
| `ColorHash.defaultBrightness` | let | public | `Modules/Images/Sources/Images/ColorHash.swift:23-23` | — | — |
| `ColorHash.str` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:30-30` | — | — |
| `ColorHash.brightness` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:31-31` | — | — |
| `ColorHash.saturation` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:32-32` | — | — |
| `ColorHash.init(_:_:_:)` | init | public | `Modules/Images/Sources/Images/ColorHash.swift:34-34` | — | — |
| `ColorHash.bkdrHash` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:40-40` | — | — |
| `ColorHash.HSB` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:53-53` | — | — |
| `ColorHash.color` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:64-64` | — | yes |
| `ColorHash.color` | var | public | `Modules/Images/Sources/Images/ColorHash.swift:69-69` | — | yes |
| `Notification.Name.FaviconDidBecomeAvailable` | let | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:21-21` | — | — |
| `FaviconDownloader` | class | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:24-24` | @MainActor | — |
| `FaviconDownloader.shared` | let | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:25-25` | — | — |
| `FaviconDownloader.UserInfoKey` | struct | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:38-38` | — | — |
| `FaviconDownloader.UserInfoKey.faviconURL` | let | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:39-39` | — | — |
| `FaviconDownloader.favicon(for:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:67-67` | — | — |
| `FaviconDownloader.faviconAsIcon(for:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:92-92` | — | — |
| `FaviconDownloader.cachedFaviconAsIcon(for:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:107-107` | — | — |
| `FaviconDownloader.cachedFaviconURL(for:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:123-123` | — | — |
| `FaviconDownloader.favicon(with:homePageURL:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:133-133` | — | — |
| `FaviconDownloader.favicon(withHomePageURL:)` | func | public | `Modules/Images/Sources/Images/FaviconDownloader.swift:141-141` | — | — |
| `FaviconGenerator` | class | public | `Modules/Images/Sources/Images/FaviconGenerator.swift:13-13` | @MainActor | — |
| `FaviconGenerator.shared` | let | public | `Modules/Images/Sources/Images/FaviconGenerator.swift:14-14` | — | — |
| `FaviconGenerator.templateImage` | var | public | `Modules/Images/Sources/Images/FaviconGenerator.swift:18-18` | — | — |
| `FaviconGenerator.favicon(_:)` | func | public | `Modules/Images/Sources/Images/FaviconGenerator.swift:35-35` | — | — |
| `Notification.Name.feedIconDidBecomeAvailable` | let | public | `Modules/Images/Sources/Images/FeedIconDownloader.swift:18-18` | — | — |
| `FeedIconDownloader` | class | public | `Modules/Images/Sources/Images/FeedIconDownloader.swift:21-21` | @MainActor | — |
| `FeedIconDownloader.shared` | let | public | `Modules/Images/Sources/Images/FeedIconDownloader.swift:23-23` | — | — |
| `FeedIconDownloader.icon(for:)` | func | public | `Modules/Images/Sources/Images/FeedIconDownloader.swift:47-47` | — | — |
| `FeedIconDownloader.cachedIcon(for:)` | func | public | `Modules/Images/Sources/Images/FeedIconDownloader.swift:157-157` | — | — |
| `HomePageFaviconRecord` | struct | public | `Modules/Images/Sources/Images/HomePageFaviconTable.swift:13-13` | — | — |
| `HomePageFaviconRecord.homePageURL` | let | public | `Modules/Images/Sources/Images/HomePageFaviconTable.swift:14-14` | — | — |
| `HomePageFaviconRecord.faviconURL` | let | public | `Modules/Images/Sources/Images/HomePageFaviconTable.swift:15-15` | — | — |
| `HomePageFaviconRecord.lastChecked` | let | public | `Modules/Images/Sources/Images/HomePageFaviconTable.swift:16-16` | — | — |
| `RSImage.maxIconPixelSize` | let | public | `Modules/Images/Sources/Images/IconImage.swift:18-18` | — | — |
| `IconImage` | class | public | `Modules/Images/Sources/Images/IconImage.swift:21-21` | — | — |
| `IconImage.image` | let | public | `Modules/Images/Sources/Images/IconImage.swift:22-22` | — | — |
| `IconImage.isSymbol` | let | public | `Modules/Images/Sources/Images/IconImage.swift:23-23` | — | — |
| `IconImage.isBackgroundSuppressed` | let | public | `Modules/Images/Sources/Images/IconImage.swift:24-24` | — | — |
| `IconImage.preferredColor` | let | public | `Modules/Images/Sources/Images/IconImage.swift:25-25` | — | — |
| `IconImage.isDark` | var | public | `Modules/Images/Sources/Images/IconImage.swift:30-30` | — | — |
| `IconImage.isBright` | var | public | `Modules/Images/Sources/Images/IconImage.swift:34-34` | — | — |
| `IconImage.init(_:isSymbol:isBackgroundSuppressed:preferredColor:)` | init | public | `Modules/Images/Sources/Images/IconImage.swift:38-38` | — | — |
| `IconSize` | enum | public | `Modules/Images/Sources/Images/IconImage.swift:99-99` | — | — |
| `IconSize.size` | var | public | `Modules/Images/Sources/Images/IconImage.swift:108-108` | — | — |
| `Notification.Name.imageDidBecomeAvailable` | let | public | `Modules/Images/Sources/Images/ImageDownloader.swift:16-16` | — | — |
| `ImageDownloadError` | struct | public | `Modules/Images/Sources/Images/ImageDownloader.swift:19-19` | — | — |
| `ImageDownloadError.statusCode` | let | public | `Modules/Images/Sources/Images/ImageDownloader.swift:20-20` | — | — |
| `ImageDownloadError.decodingFailed` | let | public | `Modules/Images/Sources/Images/ImageDownloader.swift:21-21` | — | — |
| `ImageDownloadError.isTransient` | let | public | `Modules/Images/Sources/Images/ImageDownloader.swift:22-22` | — | — |
| `ImageDownloadError.errorDescription` | var | public | `Modules/Images/Sources/Images/ImageDownloader.swift:26-26` | — | — |
| `ImageDownloader` | class | public | `Modules/Images/Sources/Images/ImageDownloader.swift:40-40` | @MainActor | — |
| `ImageDownloader.shared` | let | public | `Modules/Images/Sources/Images/ImageDownloader.swift:41-41` | — | — |
| `ImageDownloader.image(for:activityOwner:activityKind:activityDetail:)` | func | public | `Modules/Images/Sources/Images/ImageDownloader.swift:69-70` | @discardableResult | — |
| `ImageMetadataDatabase` | class | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:15-15` | @MainActor | — |
| `ImageMetadataDatabase.shared` | let | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:17-17` | — | — |
| `ImageMetadataDatabase.failureRetryDays` | let | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:19-19` | — | — |
| `ImageMetadataDatabase.databasePath` | let | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:22-22` | — | — |
| `ImageMetadataDatabase.vacuum()` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:58-58` | — | — |
| `ImageMetadataDatabase.faviconURL(forHomePageURL:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:64-64` | — | — |
| `ImageMetadataDatabase.homePageHasNoFavicon(_:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:68-68` | — | — |
| `ImageMetadataDatabase.saveHomePageFavicon(homePageURL:faviconURL:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:72-72` | — | — |
| `ImageMetadataDatabase.iconURL(forFeedURL:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:87-87` | — | — |
| `ImageMetadataDatabase.saveFeedIconURL(feedURL:iconURL:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:91-91` | — | — |
| `ImageMetadataDatabase.recentlyFailed(url:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:100-100` | — | — |
| `ImageMetadataDatabase.recordFailure(url:statusCode:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:107-107` | — | — |
| `ImageMetadataDatabase.clearFailure(url:)` | func | public | `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:114-114` | — | — |
| `Notification.Name.DidLoadFavicon` | let | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:16-16` | — | — |
| `SingleFaviconDownloader` | class | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:21-21` | @MainActor | — |
| `SingleFaviconDownloader.faviconURL` | let | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:26-26` | — | — |
| `SingleFaviconDownloader.homePageURL` | let | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:27-27` | — | — |
| `SingleFaviconDownloader.iconImage` | var | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:29-29` | — | — |
| `SingleFaviconDownloader.error` | var | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:32-32` | — | — |
| `SingleFaviconDownloader.init(faviconURL:homePageURL:diskCache:queue:)` | init | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:43-43` | — | — |
| `SingleFaviconDownloader.downloadFaviconIfNeeded()` | func | public | `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:56-56` | — | — |
| `NewsBlurFolder` | typealias | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:13-13` | — | — |
| `NewsBlurFeed` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:15-15` | — | — |
| `NewsBlurFeed.name` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:16-16` | — | — |
| `NewsBlurFeed.feedID` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:17-17` | — | — |
| `NewsBlurFeed.feedURL` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:18-18` | — | — |
| `NewsBlurFeed.homePageURL` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:19-19` | — | — |
| `NewsBlurFeed.faviconURL` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:20-20` | — | — |
| `NewsBlurFeed.init(name:feedID:feedURL:homePageURL:faviconURL:)` | init | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:22-22` | — | — |
| `NewsBlurFeedsResponse` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:31-31` | — | — |
| `NewsBlurFeedsResponse.Folder` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:35-35` | — | — |
| `NewsBlurFeedsResponse.Folder.name` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:36-36` | — | — |
| `NewsBlurFeedsResponse.Folder.feedIDs` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:37-37` | — | — |
| `NewsBlurFolderRelationship` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:45-45` | — | — |
| `NewsBlurFolderRelationship.folderName` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:46-46` | — | — |
| `NewsBlurFolderRelationship.feedID` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:47-47` | — | — |
| `NewsBlurFeedsResponse.init(from:)` | init | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:67-67` | — | — |
| `NewsBlurFeedsResponse.Folder.asRelationships` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:100-100` | — | — |
| `NewsBlurStory` | typealias | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:13-13` | — | — |
| `NewsBlurStoriesResponse` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:15-15` | — | — |
| `NewsBlurStoriesResponse.stories` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:16-16` | — | — |
| `NewsBlurStoriesResponse.Story` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:18-18` | — | — |
| `NewsBlurStoriesResponse.Story.storyID` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:19-19` | — | — |
| `NewsBlurStoriesResponse.Story.feedID` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:20-20` | — | — |
| `NewsBlurStoriesResponse.Story.title` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:21-21` | — | — |
| `NewsBlurStoriesResponse.Story.url` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:22-22` | — | — |
| `NewsBlurStoriesResponse.Story.authorName` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:23-23` | — | — |
| `NewsBlurStoriesResponse.Story.contentHTML` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:24-24` | — | — |
| `NewsBlurStoriesResponse.Story.imageURL` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:25-25` | — | — |
| `NewsBlurStoriesResponse.Story.tags` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:28-28` | — | — |
| `NewsBlurStoriesResponse.Story.datePublished` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:29-29` | — | — |
| `NewsBlurStoryHash` | typealias | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:13-13` | — | — |
| `NewsBlurStoryHashesResponse` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:15-15` | — | — |
| `NewsBlurStoryHashesResponse.StoryHashDictionary` | typealias | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:16-16` | — | — |
| `NewsBlurStoryHashesResponse.unread` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:18-18` | — | — |
| `NewsBlurStoryHashesResponse.starred` | var | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:19-19` | — | — |
| `NewsBlurStoryHashesResponse.StoryHash` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:21-21` | — | — |
| `NewsBlurStoryHashesResponse.StoryHash.hash` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:22-22` | — | — |
| `NewsBlurStoryHashesResponse.StoryHash.timestamp` | let | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:23-23` | — | — |
| `NewsBlurStoryHashesResponse.StoryHash.init(hash:timestamp:)` | init | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:25-25` | — | — |
| `NewsBlurStoryHashesResponse.init(from:)` | init | public | `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:38-38` | — | — |
| `NewsBlur` | struct | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlur.swift:12-12` | — | — |
| `NewsBlur.logger` | let | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlur.swift:14-14` | — | — |
| `NewsBlurDataConvertible` | protocol | internal | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:12-12` | — | — |
| `NewsBlurError` | enum | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:16-16` | — | — |
| `NewsBlurError.errorDescription` | var | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:21-21` | — | — |
| `NewsBlurAPICaller` | class | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:14-14` | — | — |
| `NewsBlurAPICaller.sessionIDCookieKey` | let | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:15-15` | — | — |
| `NewsBlurAPICaller.credentials` | var | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:27-27` | — | — |
| `NewsBlurAPICaller.init()` | init | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:32-32` | — | — |
| `NewsBlurAPICaller.suspend()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:36-36` | — | — |
| `NewsBlurAPICaller.resume()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:41-41` | — | — |
| `NewsBlurAPICaller.validateCredentials()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:45-45` | — | — |
| `NewsBlurAPICaller.logout()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:72-72` | — | — |
| `NewsBlurAPICaller.retrieveFeeds()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:76-76` | — | — |
| `NewsBlurAPICaller.retrieveUnreadStoryHashes()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:104-104` | — | — |
| `NewsBlurAPICaller.retrieveStarredStoryHashes()` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:108-108` | — | — |
| `NewsBlurAPICaller.retrieveStories(feedID:page:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:112-112` | — | — |
| `NewsBlurAPICaller.retrieveStories(hashes:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:127-127` | — | — |
| `NewsBlurAPICaller.markAsUnread(hashes:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:139-139` | — | — |
| `NewsBlurAPICaller.markAsRead(hashes:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:144-144` | — | — |
| `NewsBlurAPICaller.star(hashes:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:149-149` | — | — |
| `NewsBlurAPICaller.unstar(hashes:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:154-154` | — | — |
| `NewsBlurAPICaller.addFolder(named:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:159-159` | — | — |
| `NewsBlurAPICaller.renameFolder(with:to:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:164-164` | — | — |
| `NewsBlurAPICaller.removeFolder(named:feedIDs:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:169-169` | — | — |
| `NewsBlurAPICaller.addURL(_:folder:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:174-174` | — | — |
| `NewsBlurAPICaller.renameFeed(feedID:newName:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:181-181` | — | — |
| `NewsBlurAPICaller.deleteFeed(feedID:folder:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:186-186` | — | — |
| `NewsBlurAPICaller.moveFeed(feedID:from:to:)` | func | public | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:191-191` | — | — |
| `URLRequest.init(url:newsBlurCredentials:conditionalGet:)` | init | public | `Modules/NewsBlur/Sources/NewsBlur/URLRequest+NewsBlur.swift:14-14` | — | — |
| `AppConfig` | class | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:11-11` | @MainActor | — |
| `AppConfig.appName` | let | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:13-13` | — | — |
| `AppConfig.cacheFolder` | let | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:15-15` | — | — |
| `AppConfig.cacheSubfolder(named:)` | func | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:32-32` | — | — |
| `AppConfig.dataFolder` | let | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:36-36` | — | — |
| `AppConfig.dataSubfolder(named:)` | func | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:50-50` | — | — |
| `AppConfig.ensureSubfolder(named:folderURL:)` | func | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:54-54` | — | — |
| `AppConfig.relativeDataPath(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppConfig.swift:63-63` | — | — |
| `String.fourCharCode` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/FourCharCode.swift:21-21` | — | — |
| `Int.fourCharCode` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/FourCharCode.swift:32-32` | — | — |
| `KeyboardConstant` | struct | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:13-13` | — | yes |
| `KeyboardConstant.lineFeedKey` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:14-14` | — | yes |
| `KeyboardConstant.returnKey` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:15-15` | — | yes |
| `KeyboardConstant.spaceKey` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:16-16` | — | yes |
| `String.keyboardIntegerValue` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:20-20` | — | yes |
| `KeyboardShortcut` | struct | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:33-33` | — | yes |
| `KeyboardShortcut.key` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:34-34` | — | yes |
| `KeyboardShortcut.actionString` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:35-35` | — | yes |
| `KeyboardShortcut.init(dictionary:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:37-37` | — | yes |
| `KeyboardShortcut.perform(with:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:49-49` | @MainActor | yes |
| `KeyboardShortcut.findMatchingShortcut(in:key:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:54-54` | — | yes |
| `KeyboardKey` | struct | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:64-64` | — | yes |
| `KeyboardKey.shiftKeyDown` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:65-65` | — | yes |
| `KeyboardKey.optionKeyDown` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:66-66` | — | yes |
| `KeyboardKey.commandKeyDown` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:67-67` | — | yes |
| `KeyboardKey.controlKeyDown` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:68-68` | — | yes |
| `KeyboardKey.integerValue` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:69-69` | — | yes |
| `KeyboardKey.isModified` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:71-71` | — | yes |
| `KeyboardKey.init(with:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:86-86` | — | yes |
| `KeyboardKey.init(dictionary:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:98-98` | — | yes |
| `KeyboardDelegate` | protocol | public | `Modules/RSCore/Sources/RSCore/AppKit/KeyboardDelegateProtocol.swift:12-12` | @MainActor, @objc | yes |
| `TextFieldSizeInfo` | struct | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:24-24` | — | yes |
| `TextFieldSizeInfo.size` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:25-25` | — | yes |
| `TextFieldSizeInfo.numberOfLinesUsed` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:26-26` | — | yes |
| `MultilineTextFieldSizer` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:29-29` | @MainActor | yes |
| `MultilineTextFieldSizer.size(for:font:numberOfLines:width:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:55-55` | — | yes |
| `MultilineTextFieldSizer.size(for:numberOfLines:width:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:60-60` | — | yes |
| `NSAppearance.isDarkMode` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSAppearance+RSCore.swift:13-13` | @MainActor | yes |
| `NSAppleEventDescriptor.init(runningApplication:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/NSAppleEventDescriptor+RSCore.swift:19-19` | — | yes |
| `NSImage.tinted(with:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSImage+RSCore.swift:14-14` | — | yes |
| `NSMenu.takeItems(from:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSMenu+RSCore.swift:14-14` | — | yes |
| `NSMenu.addSeparatorIfNeeded()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSMenu+RSCore.swift:25-25` | — | yes |
| `NSOutlineView.selectedItems` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:13-13` | — | yes |
| `NSOutlineView.firstSelectedRow` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:23-23` | — | yes |
| `NSOutlineView.lastSelectedRow` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:31-31` | — | yes |
| `NSOutlineView.selectPreviousRow(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:39-39` | @IBAction | yes |
| `NSOutlineView.selectNextRow(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:60-60` | @IBAction | yes |
| `NSOutlineView.collapseSelectedRows(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:78-78` | @IBAction | yes |
| `NSOutlineView.expandSelectedRows(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:87-87` | @IBAction | yes |
| `NSOutlineView.expandAll(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:96-96` | @IBAction | yes |
| `NSOutlineView.collapseAllExceptForGroupItems(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:101-101` | @IBAction | yes |
| `NSOutlineView.expandAllChildren(of:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:106-106` | — | yes |
| `NSOutlineView.collapseAllChildren(of:exceptForGroupItems:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:120-120` | — | yes |
| `NSOutlineView.children(of:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:137-137` | — | yes |
| `NSOutlineView.isGroupItem(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:148-148` | — | yes |
| `NSOutlineView.canSelect(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:153-153` | — | yes |
| `NSOutlineView.canSelectItem(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:161-161` | — | yes |
| `NSOutlineView.selectItemAndScrollToVisible(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:167-167` | — | yes |
| `NSPasteboard.copyObjects(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSPasteboard+RSCore.swift:13-13` | @MainActor | yes |
| `NSPasteboard.canCopyAtLeastOneObject(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSPasteboard+RSCore.swift:22-22` | — | yes |
| `NSPasteboard.urlString(from:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSPasteboard+RSCore.swift:34-34` | — | yes |
| `NSResponder.hasAncestor(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSResponder+RSCore.swift:14-14` | — | yes |
| `NSTableView.selectionIsEmpty` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:13-13` | — | yes |
| `NSTableView.indexesOfAvailableRowsPassingTest(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:17-17` | — | yes |
| `NSTableView.indexesOfAvailableRows()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:30-30` | — | yes |
| `NSTableView.scrollTo(row:extraHeight:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:47-47` | — | yes |
| `NSTableView.scrollToRowIfNotVisible(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:70-70` | — | yes |
| `NSTableView.visibleRowViews()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:80-80` | — | yes |
| `NSTableView.selectRow(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:101-101` | — | yes |
| `NSTableView.selectRowAndScrollToVisible(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:105-105` | — | yes |
| `NSToolbar.existingItem(withIdentifier:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSToolbar+RSCore.swift:14-14` | — | yes |
| `NSView.asImage()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSView+RSCore.swift:14-14` | — | yes |
| `NSView.addFullSizeConstraints(forSubview:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSView+RSCore.swift:29-29` | — | yes |
| `NSView.constraintsToMakeSubViewFullSize(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSView+RSCore.swift:38-38` | — | yes |
| `NSView.setFrameIfNotEqual(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSView+RSCore.swift:49-49` | — | yes |
| `NSWindow.isDisplayingSheet` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:13-13` | — | yes |
| `NSWindow.makeFirstResponderUnlessDescendantIsFirstResponder(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:17-17` | — | yes |
| `NSWindow.setPointAndSizeAdjustingForScreen(point:size:minimumSize:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:24-24` | — | yes |
| `NSWindow.flippedOrigin` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:51-51` | — | yes |
| `NSWindow.setFlippedOriginAdjustingForScreen(_:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:73-73` | — | yes |
| `NSWindowController.isDisplayingSheet` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindowController+RSCore.swift:13-13` | — | yes |
| `NSWindowController.isOpen` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/NSWindowController+RSCore.swift:17-17` | — | yes |
| `PasteboardWriterOwner` | protocol | public | `Modules/RSCore/Sources/RSCore/AppKit/PasteboardWriterOwner.swift:12-12` | @MainActor | yes |
| `RSAppMovementMonitor` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/RSAppMovementMonitor.swift:13-13` | @MainActor | yes |
| `RSAppMovementMonitor.appMovementHandler` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/RSAppMovementMonitor.swift:17-17` | — | yes |
| `RSAppMovementMonitor.init()` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/RSAppMovementMonitor.swift:39-39` | — | yes |
| `RSToolbarItem` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/RSToolbarItem.swift:12-12` | — | yes |
| `RSToolbarItem.validate()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/RSToolbarItem.swift:14-14` | — | yes |
| `SingleLineTextFieldSizer` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/SingleLineTextFieldSizer.swift:17-17` | @MainActor | yes |
| `SingleLineTextFieldSizer.size(for:font:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/SingleLineTextFieldSizer.swift:24-24` | — | yes |
| `URLPasteboardWriter` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:14-14` | @objc | yes |
| `URLPasteboardWriter.init(urlString:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:17-17` | — | yes |
| `URLPasteboardWriter.write(urlString:to:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:21-21` | — | yes |
| `URLPasteboardWriter.write(urlStrings:to:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:25-25` | — | yes |
| `URLPasteboardWriter.writableTypes(for:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:38-38` | — | yes |
| `URLPasteboardWriter.pasteboardPropertyList(forType:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:45-45` | — | yes |
| `UserApp` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:16-16` | — | yes |
| `UserApp.bundleID` | let | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:17-17` | — | yes |
| `UserApp.icon` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:18-18` | — | yes |
| `UserApp.existsOnDisk` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:19-19` | — | yes |
| `UserApp.path` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:20-20` | — | yes |
| `UserApp.runningApplication` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:21-21` | — | yes |
| `UserApp.isRunning` | var | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:23-23` | — | yes |
| `UserApp.init(bundleID:)` | init | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:31-31` | — | yes |
| `UserApp.updateStatus()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:36-36` | — | yes |
| `UserApp.launchIfNeeded()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:81-81` | — | yes |
| `UserApp.bringToFront()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:120-120` | — | yes |
| `UserApp.targetDescriptor()` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:128-128` | — | yes |
| `UtilityTableView` | class | public | `Modules/RSCore/Sources/RSCore/AppKit/UtilityTableView.swift:13-13` | — | yes |
| `UtilityTableView.drawBackground(inClipRect:)` | func | public | `Modules/RSCore/Sources/RSCore/AppKit/UtilityTableView.swift:15-15` | — | yes |
| `Notification.Name.lowMemory` | let | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:14-14` | — | — |
| `Notification.Name.appDidGoToBackground` | let | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:15-15` | — | — |
| `Notification.Name.appDidBecomeActive` | let | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:16-16` | — | — |
| `AppNotification` | struct | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:19-19` | — | — |
| `AppNotification.postLowMemory()` | func | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:23-23` | — | — |
| `AppNotification.postAppDidGoToBackground()` | func | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:28-28` | — | — |
| `AppNotification.postAppDidBecomeActive()` | func | public | `Modules/RSCore/Sources/RSCore/AppNotifications.swift:33-33` | — | — |
| `Array.subscript(safe:)` | subscript | public | `Modules/RSCore/Sources/RSCore/Array+RSCore.swift:12-12` | — | — |
| `Array.chunked(into:)` | func | public | `Modules/RSCore/Sources/RSCore/Array+RSCore.swift:16-16` | — | — |
| `BatchUpdateBlock` | typealias | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:13-13` | — | — |
| `Notification.Name.BatchUpdateDidPerform` | let | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:17-17` | — | — |
| `BatchUpdate` | class | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:21-21` | @MainActor | — |
| `BatchUpdate.shared` | let | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:24-24` | — | — |
| `BatchUpdate.isPerforming` | var | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:29-29` | — | — |
| `BatchUpdate.perform(_:)` | func | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:35-35` | — | — |
| `BatchUpdate.start()` | func | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:43-43` | — | — |
| `BatchUpdate.end()` | func | public | `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:49-49` | — | — |
| `BinaryDiskCache` | class | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:12-12` | — | — |
| `BinaryDiskCache.folder` | let | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:13-13` | — | — |
| `BinaryDiskCache.init(folder:)` | init | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:16-16` | — | — |
| `BinaryDiskCache.data(forKey:)` | func | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:20-20` | — | — |
| `BinaryDiskCache.setData(_:forKey:)` | func | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:26-26` | — | — |
| `BinaryDiskCache.deleteData(forKey:)` | func | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:32-32` | — | — |
| `BinaryDiskCache.subscript(_:)` | subscript | public | `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:40-40` | — | — |
| `VoidBlock` | typealias | public | `Modules/RSCore/Sources/RSCore/Blocks.swift:11-11` | — | — |
| `VoidCompletionBlock` | typealias | public | `Modules/RSCore/Sources/RSCore/Blocks.swift:12-12` | — | — |
| `ImageResultBlock` | typealias | public | `Modules/RSCore/Sources/RSCore/Blocks.swift:14-14` | — | — |
| `Bundle.appName` | var | public | `Modules/RSCore/Sources/RSCore/Bundle+RSCore.swift:12-12` | — | — |
| `Bundle.versionNumber` | var | public | `Modules/RSCore/Sources/RSCore/Bundle+RSCore.swift:16-16` | — | — |
| `Bundle.buildNumber` | var | public | `Modules/RSCore/Sources/RSCore/Bundle+RSCore.swift:20-20` | — | — |
| `ImageLuminanceType` | enum | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:11-11` | — | — |
| `CGImage.calculateLuminanceType()` | func | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:17-17` | — | — |
| `CGImage.alpha(for:)` | func | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:107-108` | @inline | — |
| `CGImage.red(for:)` | func | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:112-113` | @inline | — |
| `CGImage.green(for:)` | func | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:117-118` | @inline | — |
| `CGImage.blue(for:)` | func | public | `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:122-123` | @inline | — |
| `CacheRecord` | protocol | public | `Modules/RSCore/Sources/RSCore/Cache.swift:11-11` | — | — |
| `Cache` | class | public | `Modules/RSCore/Sources/RSCore/Cache.swift:15-15` | — | — |
| `Cache.timeToLive` | let | public | `Modules/RSCore/Sources/RSCore/Cache.swift:17-17` | — | — |
| `Cache.timeBetweenCleanups` | let | public | `Modules/RSCore/Sources/RSCore/Cache.swift:18-18` | — | — |
| `Cache.init(timeToLive:timeBetweenCleanups:)` | init | public | `Modules/RSCore/Sources/RSCore/Cache.swift:26-26` | — | — |
| `Cache.subscript(_:)` | subscript | public | `Modules/RSCore/Sources/RSCore/Cache.swift:31-31` | — | — |
| `Cache.cleanup()` | func | public | `Modules/RSCore/Sources/RSCore/Cache.swift:55-55` | — | — |
| `Cache.removeAll()` | func | public | `Modules/RSCore/Sources/RSCore/Cache.swift:61-61` | — | — |
| `Calendar.cached` | let | public | `Modules/RSCore/Sources/RSCore/Calendar+RSCore.swift:13-13` | — | — |
| `Calendar.dateIsToday(_:)` | func | public | `Modules/RSCore/Sources/RSCore/Calendar+RSCore.swift:20-20` | — | — |
| `CoalescingQueue` | class | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:30-30` | @MainActor, @objc | — |
| `CoalescingQueue.standard` | let | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:32-32` | — | — |
| `CoalescingQueue.name` | let | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:33-33` | — | — |
| `CoalescingQueue.isPaused` | var | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:34-34` | — | — |
| `CoalescingQueue.init(name:interval:maxInterval:)` | init | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:41-41` | — | — |
| `CoalescingQueue.add(_:_:)` | func | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:47-47` | — | — |
| `CoalescingQueue.performCallsImmediately()` | func | public | `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:55-55` | — | — |
| `compareStrings(_:_:ascending:)` | func | public | `Modules/RSCore/Sources/RSCore/Comparing.swift:13-13` | — | — |
| `compareValues(_:_:ascending:)` | func | public | `Modules/RSCore/Sources/RSCore/Comparing.swift:18-18` | — | — |
| `compareOptionals(_:_:ascending:)` | func | public | `Modules/RSCore/Sources/RSCore/Comparing.swift:23-23` | — | — |
| `compareValues(_:_:)` | func | public | `Modules/RSCore/Sources/RSCore/Comparing.swift:39-39` | — | — |
| `compareOptionals(_:_:)` | func | public | `Modules/RSCore/Sources/RSCore/Comparing.swift:50-50` | — | — |
| `Data.md5Hash` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:14-14` | — | — |
| `Data.md5String` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:20-20` | — | — |
| `Data.isPNG` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:66-66` | — | — |
| `Data.isGIF` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:71-71` | — | — |
| `Data.isJPEG` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:76-76` | — | — |
| `Data.isImage` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:81-81` | — | — |
| `Data.isProbablyHTML` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:137-137` | — | — |
| `Data.hexadecimalString` | var | public | `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:207-207` | — | — |
| `Date.bySubtracting(days:)` | func | public | `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:14-14` | — | — |
| `Date.bySubtracting(hours:)` | func | public | `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:18-18` | — | — |
| `Date.byAdding(days:)` | func | public | `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:22-22` | — | — |
| `TimeInterval.init(days:)` | init | public | `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:29-29` | — | — |
| `TimeInterval.init(hours:)` | init | public | `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:33-33` | — | — |
| `DateFormatter.logTimestamp` | let | public | `Modules/RSCore/Sources/RSCore/DateFormatter+RSCore.swift:13-13` | — | — |
| `Notification.Name.DisplayNameDidChange` | let | public | `Modules/RSCore/Sources/RSCore/DisplayNameProvider.swift:12-12` | — | — |
| `DisplayNameProvider` | protocol | public | `Modules/RSCore/Sources/RSCore/DisplayNameProvider.swift:17-17` | @MainActor | — |
| `DisplayNameProvider.postDisplayNameDidChangeNotification()` | func | public | `Modules/RSCore/Sources/RSCore/DisplayNameProvider.swift:23-23` | — | — |
| `FileManager.isFolder(atPath:)` | func | public | `Modules/RSCore/Sources/RSCore/FileManager+RSCore.swift:18-18` | — | — |
| `FileManager.filenames(inFolder:)` | func | public | `Modules/RSCore/Sources/RSCore/FileManager+RSCore.swift:34-34` | — | — |
| `FileManager.filePaths(inFolder:)` | func | public | `Modules/RSCore/Sources/RSCore/FileManager+RSCore.swift:50-50` | — | — |
| `CGRect.centeredVertically(in:)` | func | public | `Modules/RSCore/Sources/RSCore/Geometry.swift:18-18` | — | — |
| `CGRect.centeredHorizontally(in:)` | func | public | `Modules/RSCore/Sources/RSCore/Geometry.swift:31-31` | — | — |
| `CGRect.centered(in:)` | func | public | `Modules/RSCore/Sources/RSCore/Geometry.swift:44-44` | — | — |
| `Array.maxY()` | func | public | `Modules/RSCore/Sources/RSCore/Geometry.swift:50-50` | — | — |
| `Logger.nnwSubsystem` | let | public | `Modules/RSCore/Sources/RSCore/Logging.swift:18-18` | — | — |
| `MacroProcessor` | class | public | `Modules/RSCore/Sources/RSCore/MacroProcessor.swift:15-15` | — | — |
| `MacroProcessor.renderedText(withTemplate:substitutions:macroStart:macroEnd:)` | func | public | `Modules/RSCore/Sources/RSCore/MacroProcessor.swift:38-38` | — | — |
| `MainThreadBlockOperation` | class | public | `Modules/RSCore/Sources/RSCore/MainThreadBlockOperation.swift:12-12` | @MainActor | — |
| `MainThreadBlockOperation.init(name:block:)` | init | public | `Modules/RSCore/Sources/RSCore/MainThreadBlockOperation.swift:15-15` | — | — |
| `MainThreadBlockOperation.run()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadBlockOperation.swift:20-20` | — | — |
| `MainThreadOperation` | class | open | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:27-27` | @MainActor | — |
| `MainThreadOperation.id` | let | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:28-28` | — | — |
| `MainThreadOperation.isCanceled` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:37-37` | — | — |
| `MainThreadOperation.name` | let | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:42-42` | — | — |
| `MainThreadOperation.MainThreadOperationCompletionBlock` | typealias | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:44-44` | — | — |
| `MainThreadOperation.completionBlock` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:45-45` | — | — |
| `MainThreadOperation.operationQueue` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:47-47` | — | — |
| `MainThreadOperation.init(name:completionBlock:)` | init | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:60-60` | — | — |
| `MainThreadOperation.run()` | func | open | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:71-71` | — | — |
| `MainThreadOperation.cancel()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:79-79` | — | — |
| `MainThreadOperation.addDependency(_:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:96-96` | — | — |
| `MainThreadOperation.didComplete()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:109-109` | — | — |
| `MainThreadOperation.noteDidComplete()` | func | open | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:122-122` | — | — |
| `MainThreadOperation.hash(into:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:132-132` | — | — |
| `MainThreadOperation.==(lhs:rhs:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:138-138` | — | — |
| `MainThreadOperationQueue` | class | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:19-19` | @MainActor | — |
| `MainThreadOperationQueue.shared` | let | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:21-21` | — | — |
| `MainThreadOperationQueue.isTrackingProgress` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:35-35` | — | — |
| `MainThreadOperationQueue.progressInfo` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:44-44` | — | — |
| `MainThreadOperationQueue.pendingOperationsCount` | var | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:52-52` | — | — |
| `MainThreadOperationQueue.init()` | init | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:57-57` | — | — |
| `MainThreadOperationQueue.add(_:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:60-60` | — | — |
| `MainThreadOperationQueue.add(_:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:76-76` | — | — |
| `MainThreadOperationQueue.cancelAll()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:83-83` | — | — |
| `MainThreadOperationQueue.cancel(_:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:97-97` | — | — |
| `MainThreadOperationQueue.cancel(named:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:114-114` | — | — |
| `MainThreadOperationQueue.suspend()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:125-125` | — | — |
| `MainThreadOperationQueue.resume()` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:131-131` | — | — |
| `MainThreadOperationQueue.operationDidComplete(_:)` | func | public | `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:137-137` | — | — |
| `MemoryPressureMonitor` | class | public | `Modules/RSCore/Sources/RSCore/MemoryPressureMonitor.swift:15-15` | — | yes |
| `MemoryPressureMonitor.shared` | let | public | `Modules/RSCore/Sources/RSCore/MemoryPressureMonitor.swift:16-16` | — | yes |
| `MemoryPressureMonitor.start()` | func | public | `Modules/RSCore/Sources/RSCore/MemoryPressureMonitor.swift:27-27` | — | yes |
| `NotificationCenter.postOnMainThread(name:object:userInfo:)` | func | public | `Modules/RSCore/Sources/RSCore/NotificationCenter+RSCore.swift:12-12` | — | — |
| `OPMLRepresentable` | protocol | public | `Modules/RSCore/Sources/RSCore/OPMLRepresentable.swift:11-11` | @MainActor | — |
| `OPMLRepresentable.OPMLString(indentLevel:)` | func | public | `Modules/RSCore/Sources/RSCore/OPMLRepresentable.swift:18-18` | — | — |
| `Platform` | struct | public | `Modules/RSCore/Sources/RSCore/Platform.swift:12-12` | — | — |
| `Platform.deviceHasiCloudAccount` | var | public | `Modules/RSCore/Sources/RSCore/Platform.swift:16-16` | — | — |
| `Platform.isRunningUnitTests` | var | public | `Modules/RSCore/Sources/RSCore/Platform.swift:21-21` | — | — |
| `Platform.dataSubfolder(forApplication:folderName:)` | func | public | `Modules/RSCore/Sources/RSCore/Platform.swift:63-63` | — | — |
| `RSImage` | typealias | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:15-15` | — | yes |
| `RSColor` | typealias | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:16-16` | — | yes |
| `RSImage` | typealias | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:21-21` | — | yes |
| `RSColor` | typealias | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:22-22` | — | yes |
| `RSImage.maskWithColor(color:)` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:33-33` | — | — |
| `RSImage.tinted(color:)` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:71-71` | @MainActor | yes |
| `RSImage.pngData()` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:90-90` | — | yes |
| `RSImage.dataRepresentation()` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:101-101` | — | — |
| `RSImage.image(data:)` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:113-113` | — | — |
| `RSImage.image(with:imageResultBlock:)` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:126-126` | — | — |
| `RSImage.scaledImageData(_:maxPixelSize:)` | func | public | `Modules/RSCore/Sources/RSCore/RSImage.swift:139-139` | — | — |
| `ProgressInfo` | struct | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:10-10` | — | — |
| `ProgressInfo.numberOfTasks` | let | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:11-11` | — | — |
| `ProgressInfo.numberCompleted` | let | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:12-12` | — | — |
| `ProgressInfo.numberRemaining` | let | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:13-13` | — | — |
| `ProgressInfo.isComplete` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:15-15` | — | — |
| `ProgressInfo.init(numberOfTasks:numberCompleted:numberRemaining:)` | init | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:19-19` | — | — |
| `ProgressInfo.combined(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:25-25` | — | — |
| `ProgressInfoReporter` | protocol | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:43-43` | @MainActor | — |
| `Notification.Name.progressInfoDidChange` | let | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:48-48` | — | — |
| `ProgressInfoReporter.postProgressInfoDidChangeNotification()` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:52-52` | — | — |
| `RSProgress` | class | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:70-70` | @MainActor | — |
| `RSProgress.numberOfTasks` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:71-71` | — | — |
| `RSProgress.numberCompleted` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:72-72` | — | — |
| `RSProgress.numberRemaining` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:73-73` | — | — |
| `RSProgress.children` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:74-74` | — | — |
| `RSProgress.progressInfo` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:77-77` | — | — |
| `RSProgress.hasNoRemainingTasks` | var | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:85-85` | — | — |
| `RSProgress.init(numberOfTasks:)` | init | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:90-90` | — | — |
| `RSProgress.updateNumberRemaining(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:98-98` | — | — |
| `RSProgress.updateNumberCompleted(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:116-116` | — | — |
| `RSProgress.addTasks(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:131-131` | — | — |
| `RSProgress.addTask()` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:140-140` | — | — |
| `RSProgress.completeTasks(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:147-147` | — | — |
| `RSProgress.completeTask()` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:159-159` | — | — |
| `RSProgress.completeAll()` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:163-163` | — | — |
| `RSProgress.reset()` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:169-169` | — | — |
| `RSProgress.addChild(_:)` | func | public | `Modules/RSCore/Sources/RSCore/RSProgress.swift:176-176` | — | — |
| `RSScreen` | class | public | `Modules/RSCore/Sources/RSCore/RSScreen.swift:12-12` | — | yes |
| `RSScreen.maxScreenScale` | var | public | `Modules/RSCore/Sources/RSCore/RSScreen.swift:14-14` | — | yes |
| `RSScreen` | class | public | `Modules/RSCore/Sources/RSCore/RSScreen.swift:24-24` | — | yes |
| `RSScreen.maxScreenScale` | let | public | `Modules/RSCore/Sources/RSCore/RSScreen.swift:25-25` | — | yes |
| `Renamable` | protocol | public | `Modules/RSCore/Sources/RSCore/Renamable.swift:12-12` | @MainActor | — |
| `SendToBlogEditorApp` | struct | public | `Modules/RSCore/Sources/RSCore/SendToBlogEditorApp.swift:14-14` | @MainActor | yes |
| `SendToBlogEditorApp.init(targetDescriptor:title:body:summary:link:permalink:subject:creator:commentsURL:guid:sourceName:sourceHomeURL:sourceFeedURL:)` | init | public | `Modules/RSCore/Sources/RSCore/SendToBlogEditorApp.swift:35-35` | — | yes |
| `SendToBlogEditorApp.send()` | func | public | `Modules/RSCore/Sources/RSCore/SendToBlogEditorApp.swift:52-52` | — | yes |
| `SendToCommand` | protocol | public | `Modules/RSCore/Sources/RSCore/SendToCommand.swift:23-23` | @MainActor | — |
| `String.htmlByAddingLink(_:className:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:16-16` | — | — |
| `String.htmlWithLink(_:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:23-23` | — | — |
| `String.hmacUsingSHA1(key:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:29-29` | — | — |
| `String.md5Hash` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:45-45` | — | — |
| `String.md5String` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:51-51` | — | — |
| `String.collapsingWhitespace` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:74-74` | — | — |
| `String.trimmingWhitespace` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:110-110` | — | — |
| `String.mayBeURL` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:138-138` | — | — |
| `String.normalizedURL` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:165-165` | — | — |
| `String.stripping(prefix:caseSensitive:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:216-216` | — | — |
| `String.stripping(suffix:caseSensitive:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:231-231` | — | — |
| `String.convertingToPlainText()` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:247-247` | — | — |
| `String.caseInsensitiveContains(_:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:281-281` | — | — |
| `String.escapingSpecialXMLCharacters` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:287-287` | — | — |
| `String.prepending(tabCount:)` | func | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:317-317` | — | — |
| `String.strippingHTTPOrHTTPSScheme` | var | public | `Modules/RSCore/Sources/RSCore/String+RSCore.swift:323-323` | — | — |
| `String.strippingHTML(maxCharacters:)` | func | public | `Modules/RSCore/Sources/RSCore/StripHTML.swift:43-43` | — | — |
| `Animations` | struct | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:12-12` | — | — |
| `Animations.select` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:15-15` | — | — |
| `Animations.scroll` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:18-18` | — | — |
| `Animations.navigation` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:21-21` | — | — |
| `Animations.rawValue` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:23-23` | — | — |
| `Animations.init(rawValue:)` | init | public | `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:24-24` | — | — |
| `CroppingPreviewParameters` | class | public | `Modules/RSCore/Sources/RSCore/UIKit/CroppingPreviewParameters.swift:13-13` | — | yes |
| `CroppingPreviewParameters.init(view:)` | init | public | `Modules/RSCore/Sources/RSCore/UIKit/CroppingPreviewParameters.swift:18-18` | — | yes |
| `ImageHeaderView` | class | public | `Modules/RSCore/Sources/RSCore/UIKit/ImageHeaderView.swift:13-13` | — | yes |
| `ImageHeaderView.rowHeight` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/ImageHeaderView.swift:14-14` | — | yes |
| `ImageHeaderView.imageView` | let | public | `Modules/RSCore/Sources/RSCore/UIKit/ImageHeaderView.swift:16-16` | — | yes |
| `ImageHeaderView.layoutSubviews()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/ImageHeaderView.swift:34-34` | — | yes |
| `NonIntrinsicImageView` | class | public | `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicImageView.swift:13-13` | — | yes |
| `NonIntrinsicImageView.intrinsicContentSize` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicImageView.swift:15-15` | — | yes |
| `NonIntrinsicLabel` | class | public | `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicLabel.swift:13-13` | — | yes |
| `NonIntrinsicLabel.intrinsicContentSize` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicLabel.swift:15-15` | — | yes |
| `PoppableGestureRecognizerDelegate` | class | public | `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:14-14` | — | yes |
| `PoppableGestureRecognizerDelegate.navigationController` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:15-15` | — | yes |
| `PoppableGestureRecognizerDelegate.gestureRecognizerShouldBegin(_:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:17-17` | — | yes |
| `PoppableGestureRecognizerDelegate.gestureRecognizer(_:shouldRecognizeSimultaneouslyWith:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:21-21` | — | yes |
| `PoppableGestureRecognizerDelegate.gestureRecognizer(_:shouldBeRequiredToFailBy:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:25-25` | — | yes |
| `SafariView` | struct | public | `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:13-13` | — | yes |
| `SafariView.init(url:)` | init | public | `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:17-17` | — | yes |
| `SafariView.makeUIViewController(context:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:21-21` | — | yes |
| `SafariView.updateUIViewController(_:context:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:25-25` | — | yes |
| `UIBarButtonItem.accEnabled` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIBarButtonItem+RSCore.swift:14-14` | @IBInspectable | yes |
| `UIBarButtonItem.accLabelText` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIBarButtonItem+RSCore.swift:23-23` | @IBInspectable | yes |
| `UICollectionView.selectItemAndScrollIfNotVisible(at:animations:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UICollectionView+RSCore.swift:17-17` | — | yes |
| `UICollectionView.middleVisibleRow()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UICollectionView+RSCore.swift:37-37` | — | yes |
| `UIFont.bold()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIFont+RSCore.swift:23-23` | — | yes |
| `UIFont.italic()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIFont+RSCore.swift:27-27` | — | yes |
| `String.height(withConstrainedWidth:font:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIFont+RSCore.swift:36-36` | — | yes |
| `String.width(withConstrainedHeight:font:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIFont+RSCore.swift:42-42` | — | yes |
| `UIPageViewController.scrollViewInsidePageControl` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIPageViewController+RSCore.swift:14-14` | — | yes |
| `UIResponder.isFirstResponderTextField` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIResponder+RSCore.swift:16-16` | — | yes |
| `UIResponder.currentFirstResponder` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIResponder+RSCore.swift:25-25` | — | yes |
| `UIStoryboard.main` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIStoryboard+RSCore.swift:16-16` | — | yes |
| `UIStoryboard.settings` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIStoryboard+RSCore.swift:20-20` | — | yes |
| `UIStoryboard.inspector` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIStoryboard+RSCore.swift:24-24` | — | yes |
| `UIStoryboard.instantiateController(ofType:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIStoryboard+RSCore.swift:28-28` | — | yes |
| `UITableView.selectRowAndScrollIfNotVisible(at:animations:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UITableView+RSCore.swift:16-16` | — | yes |
| `UITableView.cellCompletelyVisible(_:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UITableView+RSCore.swift:33-33` | — | yes |
| `UITableView.middleVisibleRow()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UITableView+RSCore.swift:38-38` | — | yes |
| `UIView.setFrameIfNotEqual(_:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIView+RSCore.swift:15-15` | — | yes |
| `UIView.asImage()` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIView+RSCore.swift:21-21` | — | yes |
| `UIViewController.presentError(title:message:dismiss:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:17-17` | — | yes |
| `ViewControllerHolder` | struct | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:31-31` | — | yes |
| `ViewControllerHolder.value` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:32-32` | — | yes |
| `ViewControllerKey` | struct | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:35-35` | — | yes |
| `ViewControllerKey.defaultValue` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:36-36` | — | yes |
| `EnvironmentValues.viewController` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:40-40` | — | yes |
| `UIViewController.present(style:builder:)` | func | public | `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:47-47` | — | yes |
| `UIWindow.topViewController` | var | public | `Modules/RSCore/Sources/RSCore/UIKit/UIWindow+RSCore.swift:14-14` | — | yes |
| `URL.percentEncodedEmailAddress` | var | public | `Modules/RSCore/Sources/RSCore/URL+RSCore.swift:13-13` | — | — |
| `URL.encodeSpacesIfNeeded(_:)` | func | public | `Modules/RSCore/Sources/RSCore/URL+RSCore.swift:26-26` | — | — |
| `UndoableCommand` | protocol | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:11-11` | @MainActor | — |
| `UndoableCommand.registerUndo()` | func | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:22-22` | — | — |
| `UndoableCommand.registerRedo()` | func | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:29-29` | — | — |
| `UndoableCommandRunner` | protocol | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:39-39` | @MainActor | — |
| `UndoableCommandRunner.runCommand(_:)` | func | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:49-49` | — | — |
| `UndoableCommandRunner.pushUndoableCommand(_:)` | func | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:54-54` | — | — |
| `UndoableCommandRunner.clearUndoableCommands()` | func | public | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:58-58` | — | — |
| `UTType.opml` | let | public | `Modules/RSCore/Sources/RSCore/UniformTypeIdentifiers+RSCore.swift:13-13` | — | — |
| `IndeterminateProgressController` | class | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/IndeterminateProgressWindowController.swift:12-12` | @MainActor | yes |
| `IndeterminateProgressController.beginProgressWithMessage(_:)` | func | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/IndeterminateProgressWindowController.swift:16-16` | — | yes |
| `IndeterminateProgressController.endProgress()` | func | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/IndeterminateProgressWindowController.swift:27-27` | — | yes |
| `WebViewWindowController` | class | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:13-13` | — | yes |
| `WebViewWindowController.init(title:)` | init | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:17-17` | — | yes |
| `WebViewWindowController.windowDidLoad()` | func | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:23-23` | — | yes |
| `WebViewWindowController.displayContents(of:)` | func | public | `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:27-27` | — | yes |
| `DatabaseBlock` | typealias | public | `Modules/RSDatabase/Sources/RSDatabase/Database.swift:13-13` | — | — |
| `DatabaseCompletionBlock` | typealias | public | `Modules/RSDatabase/Sources/RSDatabase/Database.swift:16-16` | — | — |
| `DatabaseDictionary` | typealias | public | `Modules/RSDatabase/Sources/RSDatabase/Database.swift:19-19` | — | — |
| `DatabaseQueue` | class | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:15-15` | — | — |
| `DatabaseQueue.init(databasePath:)` | init | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:31-31` | — | — |
| `DatabaseQueue.runInDatabaseSync(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:49-49` | — | — |
| `DatabaseQueue.runInDatabase(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:58-58` | — | — |
| `DatabaseQueue.runInTransactionSync(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:70-70` | — | — |
| `DatabaseQueue.runInTransaction(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:80-80` | — | — |
| `DatabaseQueue.runCreateStatements(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:90-90` | — | — |
| `DatabaseQueue.vacuum()` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:107-107` | — | — |
| `DatabaseTable` | protocol | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:12-12` | — | — |
| `DatabaseTable.selectRowsWhere(key:equals:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:21-21` | — | — |
| `DatabaseTable.selectRowsWhere(key:inValues:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:26-26` | — | — |
| `DatabaseTable.deleteRowsWhere(key:equalsAnyValue:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:35-35` | — | — |
| `DatabaseTable.updateRowsWithValue(_:valueKey:whereKey:matches:database:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:44-44` | — | — |
| `DatabaseTable.updateRowsWithDictionary(_:whereKey:matches:database:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:48-48` | — | — |
| `DatabaseTable.insertRows(_:insertType:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:54-54` | — | — |
| `DatabaseTable.insertRow(_:insertType:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:60-60` | — | — |
| `DatabaseTable.numberWithSQLAndParameters(_:_:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:66-66` | — | — |
| `DatabaseTable.containsColumn(_:in:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:75-75` | — | — |
| `FMDatabase.openAndSetUpDatabase(path:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:14-14` | — | — |
| `FMDatabase.executeUpdateInTransaction(_:withArgumentsIn:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:28-29` | @discardableResult | — |
| `FMDatabase.vacuum()` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:45-45` | — | — |
| `FMDatabase.vacuumIfNeeded(daysBetweenVacuums:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:55-55` | — | — |
| `FMDatabase.runCreateStatements(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:69-69` | — | — |
| `FMDatabase.insertRows(_:insertType:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:79-80` | @discardableResult | — |
| `FMDatabase.insertRow(_:insertType:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:90-91` | @discardableResult | — |
| `FMDatabase.updateRowsWithValue(_:valueKey:whereKey:equalsAnyValue:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:95-95` | — | — |
| `FMDatabase.updateRowsWithValue(_:valueKey:whereKey:equals:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:99-99` | — | — |
| `FMDatabase.updateRowsWithDictionary(_:whereKey:equals:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:103-103` | — | — |
| `FMDatabase.deleteRowsWhere(key:equalsAnyValue:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:107-107` | — | — |
| `FMDatabase.deleteRowsWhere(key:equals:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:111-111` | — | — |
| `FMDatabase.selectRowsWhere(key:equalsAnyValue:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:115-115` | — | — |
| `FMDatabase.count(sql:parameters:tableName:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:119-119` | — | — |
| `FMResultSet.intWithCountResult()` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:13-13` | — | — |
| `FMResultSet.compactMap(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:24-24` | — | — |
| `FMResultSet.mapToSet(_:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:35-35` | — | — |
| `FMResultSet.swiftString(forColumn:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:47-47` | — | — |
| `FMResultSet.swiftString(forColumnIndex:)` | func | public | `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:54-54` | — | — |
| `RSDatabaseInfoTable` | enum | public | `Modules/RSDatabase/Sources/RSDatabase/RSDatabaseInfoTable.swift:15-15` | — | — |
| `RSDatabaseInfoTable.tableName` | let | public | `Modules/RSDatabase/Sources/RSDatabase/RSDatabaseInfoTable.swift:17-17` | — | — |
| `RSDatabaseInfoTable.defaultDaysBetweenVacuums` | let | public | `Modules/RSDatabase/Sources/RSDatabase/RSDatabaseInfoTable.swift:18-18` | — | — |
| `FeedParserCallback` | typealias | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:14-14` | — | — |
| `FeedParser` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:16-16` | — | — |
| `FeedParser.canParse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:20-20` | — | — |
| `FeedParser.mightBeAbleToParseBasedOnPartialData(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:32-32` | — | — |
| `FeedParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:44-44` | — | — |
| `FeedParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:73-73` | — | — |
| `FeedParser.parse(_:_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:85-85` | — | — |
| `FeedParserError` | enum | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedParserError.swift:11-11` | — | — |
| `FeedType` | enum | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedType.swift:11-11` | — | — |
| `feedType(_:isPartialData:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/FeedType.swift:22-22` | — | — |
| `JSONFeedParser` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift:13-13` | — | — |
| `JSONFeedParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift:52-52` | — | — |
| `RSSInJSONParser` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/JSON/RSSInJSONParser.swift:15-15` | — | — |
| `RSSInJSONParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/JSON/RSSInJSONParser.swift:17-17` | — | — |
| `ParsedAttachment` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:11-11` | — | — |
| `ParsedAttachment.url` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:12-12` | — | — |
| `ParsedAttachment.mimeType` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:13-13` | — | — |
| `ParsedAttachment.title` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:14-14` | — | — |
| `ParsedAttachment.sizeInBytes` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:15-15` | — | — |
| `ParsedAttachment.durationInSeconds` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:16-16` | — | — |
| `ParsedAttachment.init(url:mimeType:title:sizeInBytes:durationInSeconds:)` | init | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:18-18` | — | — |
| `ParsedAttachment.hash(into:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:32-32` | — | — |
| `ParsedAuthor` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:11-11` | — | — |
| `ParsedAuthor.name` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:12-12` | — | — |
| `ParsedAuthor.url` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:13-13` | — | — |
| `ParsedAuthor.avatarURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:14-14` | — | — |
| `ParsedAuthor.emailAddress` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:15-15` | — | — |
| `ParsedAuthor.init(name:url:avatarURL:emailAddress:)` | init | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:17-17` | — | — |
| `ParsedAuthor.hash(into:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:26-26` | — | — |
| `ParsedFeed` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:11-11` | — | — |
| `ParsedFeed.type` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:12-12` | — | — |
| `ParsedFeed.title` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:13-13` | — | — |
| `ParsedFeed.homePageURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:14-14` | — | — |
| `ParsedFeed.feedURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:15-15` | — | — |
| `ParsedFeed.language` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:16-16` | — | — |
| `ParsedFeed.feedDescription` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:17-17` | — | — |
| `ParsedFeed.nextURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:18-18` | — | — |
| `ParsedFeed.iconURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:19-19` | — | — |
| `ParsedFeed.faviconURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:20-20` | — | — |
| `ParsedFeed.authors` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:21-21` | — | — |
| `ParsedFeed.expired` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:22-22` | — | — |
| `ParsedFeed.hubs` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:23-23` | — | — |
| `ParsedFeed.items` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:24-24` | — | — |
| `ParsedFeed.init(type:title:homePageURL:feedURL:language:feedDescription:nextURL:iconURL:faviconURL:authors:expired:hubs:items:)` | init | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:26-26` | — | — |
| `ParsedHub` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedHub.swift:11-11` | — | — |
| `ParsedHub.type` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedHub.swift:12-12` | — | — |
| `ParsedHub.url` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedHub.swift:13-13` | — | — |
| `ParsedItem` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:12-12` | — | — |
| `ParsedItem.syncServiceID` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:13-13` | — | — |
| `ParsedItem.uniqueID` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:14-14` | — | — |
| `ParsedItem.feedURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:15-15` | — | — |
| `ParsedItem.url` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:16-16` | — | — |
| `ParsedItem.externalURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:17-17` | — | — |
| `ParsedItem.title` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:18-18` | — | — |
| `ParsedItem.language` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:19-19` | — | — |
| `ParsedItem.contentHTML` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:20-20` | — | — |
| `ParsedItem.contentText` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:21-21` | — | — |
| `ParsedItem.markdown` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:22-22` | — | — |
| `ParsedItem.summary` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:23-23` | — | — |
| `ParsedItem.imageURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:24-24` | — | — |
| `ParsedItem.bannerImageURL` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:25-25` | — | — |
| `ParsedItem.datePublished` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:26-26` | — | — |
| `ParsedItem.dateModified` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:27-27` | — | — |
| `ParsedItem.authors` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:28-28` | — | — |
| `ParsedItem.tags` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:29-29` | — | — |
| `ParsedItem.attachments` | let | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:30-30` | — | — |
| `ParsedItem.init(syncServiceID:uniqueID:feedURL:url:externalURL:title:language:contentHTML:contentText:markdown:summary:imageURL:bannerImageURL:datePublished:dateModified:authors:tags:attachments:)` | init | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:32-32` | — | — |
| `ParsedItem.hash(into:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:79-79` | — | — |
| `AtomParser` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/AtomParser.swift:10-10` | — | — |
| `AtomParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/AtomParser.swift:12-12` | — | — |
| `OPMLParser` | enum | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/OPMLParser.swift:10-10` | — | — |
| `OPMLParser.parseOPML(with:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/OPMLParser.swift:13-13` | — | — |
| `RSSParser` | struct | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/RSSParser.swift:10-10` | — | — |
| `RSSParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/Feeds/XML/RSSParser.swift:12-12` | — | — |
| `HTMLAttributes` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:16-16` | — | — |
| `HTMLAttributes.empty` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:24-24` | — | — |
| `HTMLAttributes.count` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:26-26` | — | — |
| `HTMLAttributes.isEmpty` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:30-30` | — | — |
| `HTMLAttributes.subscript(name:)` | subscript | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:35-35` | — | — |
| `HTMLAttributes.dictionary()` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLAttributes.swift:56-56` | — | — |
| `HTMLLink` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLink.swift:11-11` | — | — |
| `HTMLLink.urlString` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLink.swift:12-12` | — | — |
| `HTMLLink.text` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLink.swift:13-13` | — | — |
| `HTMLLink.title` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLink.swift:14-14` | — | — |
| `HTMLLink.init(urlString:text:title:)` | init | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLink.swift:16-16` | — | — |
| `HTMLLinkParser` | enum | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLinkParser.swift:18-18` | — | — |
| `HTMLLinkParser.htmlLinks(with:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLLinkParser.swift:20-20` | — | — |
| `HTMLMetadata` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:14-14` | — | — |
| `HTMLMetadata.baseURLString` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:16-16` | — | — |
| `HTMLMetadata.tags` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:17-17` | — | — |
| `HTMLMetadata.favicons` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:18-18` | — | — |
| `HTMLMetadata.appleTouchIcons` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:19-19` | — | — |
| `HTMLMetadata.feedLinks` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:20-20` | — | — |
| `HTMLMetadata.openGraphProperties` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:21-21` | — | — |
| `HTMLMetadata.twitterProperties` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:22-22` | — | — |
| `HTMLMetadata.init(urlString:tags:)` | init | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:24-24` | — | — |
| `HTMLMetadataFeedLink` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:35-35` | — | — |
| `HTMLMetadataFeedLink.title` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:36-36` | — | — |
| `HTMLMetadataFeedLink.type` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:37-37` | — | — |
| `HTMLMetadataFeedLink.urlString` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:38-38` | — | — |
| `HTMLMetadataFavicon` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:41-41` | — | — |
| `HTMLMetadataFavicon.type` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:42-42` | — | — |
| `HTMLMetadataFavicon.urlString` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:43-43` | — | — |
| `HTMLMetadataAppleTouchIcon` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:46-46` | — | — |
| `HTMLMetadataAppleTouchIcon.rel` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:47-47` | — | — |
| `HTMLMetadataAppleTouchIcon.sizes` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:48-48` | — | — |
| `HTMLMetadataAppleTouchIcon.size` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:49-49` | — | — |
| `HTMLMetadataAppleTouchIcon.urlString` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:50-50` | — | — |
| `HTMLOpenGraphProperties` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:53-53` | — | — |
| `HTMLOpenGraphProperties.images` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:54-54` | — | — |
| `HTMLOpenGraphImage` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:61-61` | — | — |
| `HTMLOpenGraphImage.url` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:62-62` | — | — |
| `HTMLOpenGraphImage.secureURL` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:63-63` | — | — |
| `HTMLOpenGraphImage.mimeType` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:64-64` | — | — |
| `HTMLOpenGraphImage.width` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:65-65` | — | — |
| `HTMLOpenGraphImage.height` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:66-66` | — | — |
| `HTMLOpenGraphImage.altText` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:67-67` | — | — |
| `HTMLTwitterProperties` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:70-70` | — | — |
| `HTMLTwitterProperties.imageURL` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:71-71` | — | — |
| `HTMLMetadataParser` | enum | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadataParser.swift:19-19` | — | — |
| `HTMLMetadataParser.htmlMetadata(with:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadataParser.swift:21-21` | — | — |
| `HTMLRelativeURLResolver` | enum | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLRelativeURLResolver.swift:22-22` | — | — |
| `HTMLRelativeURLResolver.resolvingRelativeURLs(in:baseURL:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLRelativeURLResolver.swift:24-24` | — | — |
| `HTMLRelativeURLResolver.resolvingRelativeURLs(inBytes:baseURL:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLRelativeURLResolver.swift:32-32` | — | — |
| `HTMLScanner` | class | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:24-24` | — | — |
| `HTMLScanner.delegate` | var | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:26-26` | — | — |
| `HTMLScanner.init(delegate:)` | init | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:28-28` | — | — |
| `HTMLScanner.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:32-32` | — | — |
| `HTMLScannerDelegate` | protocol | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:480-480` | — | — |
| `HTMLScannerDelegate.htmlScanner(_:didStartTag:attributes:selfClosing:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:502-502` | — | — |
| `HTMLScannerDelegate.htmlScanner(_:didEndTag:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:507-507` | — | — |
| `HTMLScannerDelegate.htmlScanner(_:didFindCharacters:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:510-510` | — | — |
| `HTMLScannerDelegate.htmlScannerDidEnd(_:)` | func | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:513-513` | — | — |
| `HTMLTag` | struct | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLTag.swift:12-12` | — | — |
| `HTMLTag.TagType` | enum | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLTag.swift:14-14` | — | — |
| `HTMLTag.type` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLTag.swift:19-19` | — | — |
| `HTMLTag.attributes` | let | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLTag.swift:20-20` | — | — |
| `HTMLTag.init(type:attributes:)` | init | public | `Modules/RSParser/Sources/RSParser/HTML/HTMLTag.swift:22-22` | — | — |
| `JSONDictionary` | typealias | public | `Modules/RSParser/Sources/RSParser/JSON/JSONTypes.swift:11-11` | — | — |
| `JSONArray` | typealias | public | `Modules/RSParser/Sources/RSParser/JSON/JSONTypes.swift:12-12` | — | — |
| `JSONUtilities` | struct | public | `Modules/RSParser/Sources/RSParser/JSON/JSONUtilities.swift:11-11` | — | — |
| `JSONUtilities.object(with:)` | func | public | `Modules/RSParser/Sources/RSParser/JSON/JSONUtilities.swift:13-13` | — | — |
| `JSONUtilities.dictionary(with:)` | func | public | `Modules/RSParser/Sources/RSParser/JSON/JSONUtilities.swift:17-17` | — | — |
| `JSONUtilities.array(with:)` | func | public | `Modules/RSParser/Sources/RSParser/JSON/JSONUtilities.swift:21-21` | — | — |
| `Dictionary.opmlText` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:14-14` | — | — |
| `Dictionary.opmlTitle` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:15-15` | — | — |
| `Dictionary.opmlDescription` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:16-16` | — | — |
| `Dictionary.opmlType` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:17-17` | — | — |
| `Dictionary.opmlVersion` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:18-18` | — | — |
| `Dictionary.opmlHMTLURL` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:19-19` | — | — |
| `Dictionary.opmlXMLURL` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLAttributes.swift:20-20` | — | — |
| `OPMLDocument` | class | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLDocument.swift:11-11` | — | — |
| `OPMLDocument.title` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLDocument.swift:13-13` | — | — |
| `OPMLDocument.url` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLDocument.swift:14-14` | — | — |
| `OPMLDocument.init(url:)` | init | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLDocument.swift:16-16` | — | — |
| `OPMLError` | enum | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLError.swift:10-10` | — | — |
| `OPMLError.errorDescription` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLError.swift:13-13` | — | — |
| `OPMLError.failureReason` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLError.swift:20-20` | — | — |
| `OPMLFeedSpecifier` | struct | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:8-8` | — | — |
| `OPMLFeedSpecifier.title` | let | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:10-10` | — | — |
| `OPMLFeedSpecifier.feedDescription` | let | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:11-11` | — | — |
| `OPMLFeedSpecifier.homePageURL` | let | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:12-12` | — | — |
| `OPMLFeedSpecifier.feedURL` | let | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:13-13` | — | — |
| `OPMLFeedSpecifier.init(title:feedDescription:homePageURL:feedURL:)` | init | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLFeedSpecifier.swift:15-15` | — | — |
| `OPMLItem` | class | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:15-15` | — | — |
| `OPMLItem.attributes` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:17-17` | — | — |
| `OPMLItem.children` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:18-18` | — | — |
| `OPMLItem.init(attributes:)` | init | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:20-20` | — | — |
| `OPMLItem.addChild(_:)` | func | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:24-24` | — | — |
| `OPMLItem.titleFromAttributes` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:32-32` | — | — |
| `OPMLItem.isFolder` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:40-40` | — | — |
| `OPMLItem.feedSpecifier` | var | public | `Modules/RSParser/Sources/RSParser/OPML/OPMLItem.swift:46-46` | — | — |
| `ParserData` | struct | public | `Modules/RSParser/Sources/RSParser/ParserData.swift:12-12` | — | — |
| `ParserData.url` | let | public | `Modules/RSParser/Sources/RSParser/ParserData.swift:14-14` | — | — |
| `ParserData.data` | let | public | `Modules/RSParser/Sources/RSParser/ParserData.swift:15-15` | — | — |
| `ParserData.init(url:data:)` | init | public | `Modules/RSParser/Sources/RSParser/ParserData.swift:17-17` | — | — |
| `DateParser` | enum | public | `Modules/RSParser/Sources/RSParser/Utilities/DateParser.swift:18-18` | — | — |
| `DateParser.date(from:)` | func | public | `Modules/RSParser/Sources/RSParser/Utilities/DateParser.swift:21-21` | — | — |
| `String.decodingHTMLEntities()` | func | public | `Modules/RSParser/Sources/RSParser/XML/String+HTMLEntities.swift:16-16` | — | — |
| `ArraySlice.equals(_:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLASCII.swift:99-99` | — | — |
| `ArraySlice.equalsASCIICaseInsensitive(lowercaseLiteral:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLASCII.swift:118-118` | — | — |
| `XMLAttributes` | struct | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:16-16` | — | — |
| `XMLAttributes.empty` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:45-45` | — | — |
| `XMLAttributes.count` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:47-47` | — | — |
| `XMLAttributes.isEmpty` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:51-51` | — | — |
| `XMLAttributes.subscript(name:)` | subscript | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:59-59` | — | — |
| `XMLAttributes.value(forNameCaseInsensitive:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:65-65` | — | — |
| `XMLAttributes.dictionary()` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:70-70` | — | — |
| `XMLAttributes.forEach(_:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLAttributes.swift:80-80` | — | — |
| `XMLNamespace` | struct | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:18-18` | — | — |
| `XMLNamespace.prefix` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:22-22` | — | — |
| `XMLNamespace.uri` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:25-25` | — | — |
| `XMLNamespace.init(prefix:uri:)` | init | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:27-27` | — | — |
| `XMLNamespace.isAtom` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:34-34` | — | — |
| `XMLNamespace.isDublinCore` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:39-39` | — | — |
| `XMLNamespace.isContent` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:43-43` | — | — |
| `XMLNamespace.isXHTML` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:47-47` | — | — |
| `XMLNamespace.isMediaRSS` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:51-51` | — | — |
| `XMLNamespace.isITunes` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:55-55` | — | — |
| `XMLNamespace.isSource` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:61-61` | — | — |
| `XMLNamespace.URI` | enum | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:67-67` | — | — |
| `XMLNamespace.URI.atom` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:68-68` | — | — |
| `XMLNamespace.URI.dublinCore` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:69-69` | — | — |
| `XMLNamespace.URI.dublinCoreTerms` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:70-70` | — | — |
| `XMLNamespace.URI.content` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:71-71` | — | — |
| `XMLNamespace.URI.xhtml` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:72-72` | — | — |
| `XMLNamespace.URI.mediaRSS` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:73-73` | — | — |
| `XMLNamespace.URI.itunes` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:74-74` | — | — |
| `XMLNamespace.URI.source` | let | public | `Modules/RSParser/Sources/RSParser/XML/XMLNamespace.swift:75-75` | — | — |
| `XMLSAXParser` | class | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:23-23` | — | — |
| `XMLSAXParser.delegate` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:25-25` | — | — |
| `XMLSAXParser.init(delegate:)` | init | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:42-42` | — | — |
| `XMLSAXParser.captureRawInnerContent()` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:54-54` | — | — |
| `XMLSAXParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:60-60` | — | — |
| `XMLSAXParser.parse(_:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:64-64` | — | — |
| `XMLSAXParser.beginStoringCharacters()` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:99-99` | — | — |
| `XMLSAXParser.endStoringCharacters()` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:107-107` | — | — |
| `XMLSAXParser.currentCharacters` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:114-114` | — | — |
| `XMLSAXParser.currentStringWithTrimmedWhitespace` | var | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:118-118` | — | — |
| `XMLSAXParserDelegate` | protocol | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:20-20` | — | — |
| `XMLSAXParserDelegate.xmlSAXParser(_:didStartElement:namespace:attributes:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:62-62` | — | — |
| `XMLSAXParserDelegate.xmlSAXParser(_:didEndElement:namespace:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:67-67` | — | — |
| `XMLSAXParserDelegate.xmlSAXParser(_:didFindCharacters:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:71-71` | — | — |
| `XMLSAXParserDelegate.xmlSAXParser(_:didCaptureRawInnerContent:forElement:namespace:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:74-74` | — | — |
| `XMLSAXParserDelegate.xmlSAXParserDidEnd(_:)` | func | public | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:79-79` | — | — |
| `NSOutlineView.revealAndSelectNodeAtPath(_:)` | func | public | `Modules/RSTree/Sources/RSTree/NSOutlineView+RSTree.swift:15-16` | @discardableResult | yes |
| `NSOutlineView.revealAndSelectRepresentedObject(_:_:)` | func | public | `Modules/RSTree/Sources/RSTree/NSOutlineView+RSTree.swift:47-48` | @discardableResult | yes |
| `Node` | class | public | `Modules/RSTree/Sources/RSTree/Node.swift:11-11` | @MainActor | — |
| `Node.parent` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:12-12` | — | — |
| `Node.representedObject` | let | public | `Modules/RSTree/Sources/RSTree/Node.swift:13-13` | — | — |
| `Node.canHaveChildNodes` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:14-14` | — | — |
| `Node.isGroupItem` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:15-15` | — | — |
| `Node.childNodes` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:16-16` | — | — |
| `Node.uniqueID` | let | public | `Modules/RSTree/Sources/RSTree/Node.swift:17-17` | — | — |
| `Node.isRoot` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:20-20` | — | — |
| `Node.numberOfChildNodes` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:24-24` | — | — |
| `Node.indexPath` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:28-28` | — | — |
| `Node.level` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:39-39` | — | — |
| `Node.isLeaf` | var | public | `Modules/RSTree/Sources/RSTree/Node.swift:46-46` | — | — |
| `Node.init(representedObject:parent:)` | init | public | `Modules/RSTree/Sources/RSTree/Node.swift:50-50` | — | — |
| `Node.genericRootNode()` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:60-60` | — | — |
| `Node.existingOrNewChildNode(with:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:66-66` | — | — |
| `Node.createChildNode(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:73-73` | — | — |
| `Node.childAtIndex(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:78-78` | — | — |
| `Node.indexOfChild(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:85-85` | — | — |
| `Node.childNodeRepresentingObject(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:89-89` | — | — |
| `Node.descendantNodeRepresentingObject(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:93-93` | — | — |
| `Node.descendantNode(where:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:97-97` | — | — |
| `Node.hasAncestor(in:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:101-101` | — | — |
| `Node.isAncestor(of:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:110-110` | — | — |
| `Node.nodesOrganizedByParent(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:127-127` | — | — |
| `Node.indexSetsGroupedByParent(_:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:132-132` | — | — |
| `Node.hash(into:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:156-156` | — | — |
| `Node.==(lhs:rhs:)` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:162-162` | — | — |
| `Array.representedObjects()` | func | public | `Modules/RSTree/Sources/RSTree/Node.swift:169-169` | — | — |
| `NodePath` | struct | public | `Modules/RSTree/Sources/RSTree/NodePath.swift:11-11` | @MainActor | — |
| `NodePath.init(node:)` | init | public | `Modules/RSTree/Sources/RSTree/NodePath.swift:14-14` | — | — |
| `NodePath.init(representedObject:treeController:)` | init | public | `Modules/RSTree/Sources/RSTree/NodePath.swift:31-31` | — | — |
| `TreeControllerDelegate` | protocol | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:11-11` | @MainActor | — |
| `NodeVisitBlock` | typealias | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:15-15` | — | — |
| `TreeController` | class | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:17-17` | @MainActor | — |
| `TreeController.rootNode` | let | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:20-20` | — | — |
| `TreeController.init(delegate:rootNode:)` | init | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:22-22` | — | — |
| `TreeController.init(delegate:)` | init | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:28-28` | — | — |
| `TreeController.rebuild()` | func | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:32-33` | @discardableResult | — |
| `TreeController.visitNodes(_:)` | func | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:39-39` | — | — |
| `TreeController.nodeInArrayRepresentingObject(nodes:representedObject:recurse:)` | func | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:43-43` | — | — |
| `TreeController.nodeInTreeRepresentingObject(_:)` | func | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:60-60` | — | — |
| `TreeController.normalizedSelectedNodes(_:)` | func | public | `Modules/RSTree/Sources/RSTree/TreeController.swift:64-64` | — | — |
| `CacheControlInfo` | struct | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:13-13` | — | — |
| `CacheControlInfo.dateCreated` | let | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:15-15` | — | — |
| `CacheControlInfo.maxAge` | let | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:16-16` | — | — |
| `CacheControlInfo.canResume` | var | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:21-21` | — | — |
| `CacheControlInfo.canResume(maxMaxAge:)` | func | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:29-29` | — | — |
| `CacheControlInfo.init(dateCreated:maxAge:)` | init | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:34-34` | — | — |
| `CacheControlInfo.init(urlResponse:)` | init | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:39-39` | — | — |
| `CacheControlInfo.init(value:)` | init | public | `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:47-47` | — | — |
| `Dictionary.urlQueryString` | var | public | `Modules/RSWeb/Sources/RSWeb/Dictionary+RSWeb.swift:14-14` | — | — |
| `DownloadResponse` | struct | public | `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:11-11` | — | — |
| `DownloadResponse.data` | let | public | `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:13-13` | — | — |
| `DownloadResponse.response` | let | public | `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:14-14` | — | — |
| `DownloadResponse.returnedFromCache` | let | public | `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:18-18` | — | — |
| `DownloadResponse.init(data:response:returnedFromCache:)` | init | public | `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:20-20` | — | — |
| `DownloadSessionDelegate` | protocol | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:16-16` | @MainActor | — |
| `DownloadSession` | class | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:38-38` | @MainActor, @objc | — |
| `DownloadSession.progressInfo` | var | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:48-48` | — | — |
| `DownloadSession.init(delegate:)` | init | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:65-65` | — | — |
| `DownloadSession.recreateURLSession()` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:76-76` | — | — |
| `DownloadSession.cancelAll()` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:106-106` | — | — |
| `DownloadSession.download(_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:124-124` | @MainActor | — |
| `DownloadSession.urlSession(_:task:didCompleteWithError:)` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:147-147` | — | — |
| `DownloadSession.urlSession(_:task:willPerformHTTPRedirection:newRequest:completionHandler:)` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:168-168` | — | — |
| `DownloadSession.urlSession(_:dataTask:didReceive:completionHandler:)` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:193-193` | — | — |
| `DownloadSession.urlSession(_:dataTask:didReceive:)` | func | public | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:233-233` | — | — |
| `DownloadCallback` | typealias | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:13-13` | — | — |
| `Downloader` | class | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:18-18` | @MainActor | — |
| `Downloader.shared` | let | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:19-19` | — | — |
| `Downloader.download(_:userAgentStyle:)` | func | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:45-45` | — | — |
| `Downloader.download(_:userAgentStyle:)` | func | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:49-49` | — | — |
| `Downloader.download(_:userAgentStyle:_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:61-61` | — | — |
| `Downloader.download(_:userAgentStyle:_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/Downloader.swift:66-66` | — | — |
| `HTTPConditionalGetInfo` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:11-11` | — | — |
| `HTTPConditionalGetInfo.lastModified` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:13-13` | — | — |
| `HTTPConditionalGetInfo.etag` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:14-14` | — | — |
| `HTTPConditionalGetInfo.init(lastModified:etag:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:16-16` | — | — |
| `HTTPConditionalGetInfo.init(urlResponse:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:24-24` | — | — |
| `HTTPConditionalGetInfo.init(headers:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:30-30` | — | — |
| `HTTPConditionalGetInfo.addRequestHeadersToURLRequest(_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:36-36` | — | — |
| `HTTPDateInfo` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPDateInfo.swift:11-11` | — | — |
| `HTTPDateInfo.date` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPDateInfo.swift:20-20` | — | — |
| `HTTPDateInfo.init(urlResponse:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPDateInfo.swift:22-22` | — | — |
| `HTTPLinkPagingInfo` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:11-11` | — | — |
| `HTTPLinkPagingInfo.nextPage` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:12-12` | — | — |
| `HTTPLinkPagingInfo.lastPage` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:13-13` | — | — |
| `HTTPLinkPagingInfo.init(nextPage:lastPage:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:15-15` | — | — |
| `HTTPLinkPagingInfo.init(urlResponse:)` | init | public | `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:20-20` | — | — |
| `HTTPMethod` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:11-11` | — | — |
| `HTTPMethod.get` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:12-12` | — | — |
| `HTTPMethod.post` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:13-13` | — | — |
| `HTTPMethod.put` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:14-14` | — | — |
| `HTTPMethod.patch` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:15-15` | — | — |
| `HTTPMethod.delete` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:16-16` | — | — |
| `HTTPRequestHeader` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:11-11` | — | — |
| `HTTPRequestHeader.userAgent` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:13-13` | — | — |
| `HTTPRequestHeader.authorization` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:14-14` | — | — |
| `HTTPRequestHeader.contentType` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:15-15` | — | — |
| `HTTPRequestHeader.ifModifiedSince` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:19-19` | — | — |
| `HTTPRequestHeader.ifNoneMatch` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:20-20` | — | — |
| `HTTPResponseCode` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:11-11` | — | — |
| `HTTPResponseCode.responseContinue` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:16-16` | — | — |
| `HTTPResponseCode.switchingProtocols` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:17-17` | — | — |
| `HTTPResponseCode.OK` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:19-19` | — | — |
| `HTTPResponseCode.created` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:20-20` | — | — |
| `HTTPResponseCode.accepted` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:21-21` | — | — |
| `HTTPResponseCode.nonAuthoritativeInformation` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:22-22` | — | — |
| `HTTPResponseCode.noContent` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:23-23` | — | — |
| `HTTPResponseCode.resetContent` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:24-24` | — | — |
| `HTTPResponseCode.partialContent` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:25-25` | — | — |
| `HTTPResponseCode.redirectMultipleChoices` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:27-27` | — | — |
| `HTTPResponseCode.redirectPermanent` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:28-28` | — | — |
| `HTTPResponseCode.redirectTemporary` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:29-29` | — | — |
| `HTTPResponseCode.redirectSeeOther` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:30-30` | — | — |
| `HTTPResponseCode.notModified` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:31-31` | — | — |
| `HTTPResponseCode.useProxy` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:32-32` | — | — |
| `HTTPResponseCode.unused` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:33-33` | — | — |
| `HTTPResponseCode.redirectVeryTemporary` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:34-34` | — | — |
| `HTTPResponseCode.redirectPermanentPreservingMethod` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:35-35` | — | — |
| `HTTPResponseCode.badRequest` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:37-37` | — | — |
| `HTTPResponseCode.unauthorized` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:38-38` | — | — |
| `HTTPResponseCode.paymentRequired` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:39-39` | — | — |
| `HTTPResponseCode.forbidden` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:40-40` | — | — |
| `HTTPResponseCode.notFound` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:41-41` | — | — |
| `HTTPResponseCode.methodNotAllowed` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:42-42` | — | — |
| `HTTPResponseCode.notAcceptable` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:43-43` | — | — |
| `HTTPResponseCode.proxyAuthenticationRequired` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:44-44` | — | — |
| `HTTPResponseCode.requestTimeout` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:45-45` | — | — |
| `HTTPResponseCode.conflict` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:46-46` | — | — |
| `HTTPResponseCode.gone` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:47-47` | — | — |
| `HTTPResponseCode.lengthRequired` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:48-48` | — | — |
| `HTTPResponseCode.preconditionFailed` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:49-49` | — | — |
| `HTTPResponseCode.entityTooLarge` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:50-50` | — | — |
| `HTTPResponseCode.URITooLong` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:51-51` | — | — |
| `HTTPResponseCode.unsupportedMediaType` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:52-52` | — | — |
| `HTTPResponseCode.requestedRangeNotSatisfiable` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:53-53` | — | — |
| `HTTPResponseCode.expectationFailed` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:54-54` | — | — |
| `HTTPResponseCode.imATeapot` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:55-55` | — | — |
| `HTTPResponseCode.misdirectedRequest` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:56-56` | — | — |
| `HTTPResponseCode.unprocessableContentWebDAV` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:57-57` | — | — |
| `HTTPResponseCode.lockedWebDAV` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:58-58` | — | — |
| `HTTPResponseCode.failedDependencyWebDAV` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:59-59` | — | — |
| `HTTPResponseCode.tooEarly` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:60-60` | — | — |
| `HTTPResponseCode.upgradeRequired` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:61-61` | — | — |
| `HTTPResponseCode.preconditionRequired` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:62-62` | — | — |
| `HTTPResponseCode.tooManyRequests` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:63-63` | — | — |
| `HTTPResponseCode.requestHeaderFieldsTooLarge` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:64-64` | — | — |
| `HTTPResponseCode.unavailableForLegalReasons` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:65-65` | — | — |
| `HTTPResponseCode.internalServerError` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:67-67` | — | — |
| `HTTPResponseCode.notImplemented` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:68-68` | — | — |
| `HTTPResponseCode.badGateway` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:69-69` | — | — |
| `HTTPResponseCode.serviceUnavailable` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:70-70` | — | — |
| `HTTPResponseCode.gatewayTimeout` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:71-71` | — | — |
| `HTTPResponseCode.HTTPVersionNotSupported` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:72-72` | — | — |
| `HTTPResponseHeader` | struct | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:11-11` | — | — |
| `HTTPResponseHeader.contentType` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:13-13` | — | — |
| `HTTPResponseHeader.location` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:14-14` | — | — |
| `HTTPResponseHeader.link` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:15-15` | — | — |
| `HTTPResponseHeader.date` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:16-16` | — | — |
| `HTTPResponseHeader.lastModified` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:21-21` | — | — |
| `HTTPResponseHeader.etag` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:24-24` | — | — |
| `HTTPResponseHeader.cacheControl` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:26-26` | — | — |
| `HTTPResponseHeader.retryAfter` | let | public | `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:27-27` | — | — |
| `MacWebBrowser` | class | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:13-13` | @MainActor | yes |
| `MacWebBrowser.openURL(_:inBackground:)` | func | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:16-16` | @discardableResult | yes |
| `MacWebBrowser.sortedBrowsers()` | func | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:37-37` | — | yes |
| `MacWebBrowser.duplicateBrowserNames(in:)` | func | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:58-58` | — | yes |
| `MacWebBrowser.displayPath(of:)` | func | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:82-82` | — | yes |
| `MacWebBrowser.ʼdefaultʼ` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:103-103` | — | yes |
| `MacWebBrowser.url` | let | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:108-108` | — | yes |
| `MacWebBrowser.icon` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:119-119` | — | yes |
| `MacWebBrowser.name` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:136-136` | — | yes |
| `MacWebBrowser.bundleIdentifier` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:145-145` | — | yes |
| `MacWebBrowser.bundlePath` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:150-150` | — | yes |
| `MacWebBrowser.init(url:)` | init | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:156-156` | — | yes |
| `MacWebBrowser.init(bundleIdentifier:)` | init | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:162-162` | — | yes |
| `MacWebBrowser.init(path:)` | init | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:173-173` | — | yes |
| `MacWebBrowser.openURL(_:inBackground:)` | func | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:184-184` | @discardableResult | yes |
| `MacWebBrowser.debugDescription` | var | public | `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:208-208` | — | yes |
| `MimeType` | struct | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:11-11` | — | — |
| `MimeType.png` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:15-15` | — | — |
| `MimeType.jpeg` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:16-16` | — | — |
| `MimeType.jpg` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:17-17` | — | — |
| `MimeType.gif` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:18-18` | — | — |
| `MimeType.tiff` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:19-19` | — | — |
| `MimeType.formURLEncoded` | let | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:21-21` | — | — |
| `String.isMimeTypeImage()` | func | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:26-26` | — | — |
| `String.isMimeTypeAudio()` | func | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:31-31` | — | — |
| `String.isMimeTypeVideo()` | func | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:36-36` | — | — |
| `String.isMimeTypeTimeBasedMedia()` | func | public | `Modules/RSWeb/Sources/RSWeb/MimeType.swift:41-41` | — | — |
| `NetworkMonitor` | class | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:12-12` | — | — |
| `NetworkMonitor.shared` | let | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:13-13` | — | — |
| `NetworkMonitor.isConnected` | var | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:29-29` | — | — |
| `NetworkMonitor.connectionType` | var | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:33-33` | — | — |
| `NetworkMonitor.isExpensive` | var | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:38-38` | — | — |
| `NetworkMonitor.isConstrained` | var | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:43-43` | — | — |
| `NetworkMonitor.start()` | func | public | `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:57-57` | @MainActor | — |
| `localeForLowercasing` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:11-11` | — | — |
| `SpecialCase` | struct | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:13-13` | — | — |
| `SpecialCase.rachelByTheBayHostName` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:14-14` | — | — |
| `SpecialCase.openRSSOrgHostName` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:15-15` | — | — |
| `SpecialCase.youtubeHostName` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:16-16` | — | — |
| `SpecialCase.redditHostName` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:17-17` | — | — |
| `SpecialCase.relayFMHostName` | let | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:18-18` | — | — |
| `SpecialCase.urlStringContainSpecialCase(_:_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:20-20` | — | — |
| `SpecialCase.urlStringMatchesDomain(_:_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:36-36` | — | — |
| `URL.isOpenRSSOrgURL` | var | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:64-64` | — | — |
| `URL.isRachelByTheBayURL` | var | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:71-71` | — | — |
| `URL.isYoutubeURL` | var | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:78-78` | — | — |
| `URL.isRedditURL` | var | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:85-85` | — | — |
| `URL.isRelayFMBlogURL` | var | public | `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:91-91` | — | — |
| `String.escapedHTML` | var | public | `Modules/RSWeb/Sources/RSWeb/String+RSWeb.swift:16-16` | — | — |
| `URL.isHTTPSURL()` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:22-22` | — | — |
| `URL.isHTTPURL()` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:26-26` | — | — |
| `URL.isHTTPOrHTTPSURL()` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:30-30` | — | — |
| `URL.absoluteStringWithHTTPOrHTTPSPrefixRemoved()` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:34-34` | — | — |
| `URL.appendingQueryItem(_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:46-46` | — | — |
| `URL.appendingQueryItems(_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:50-50` | — | — |
| `URL.preparedForOpeningInBrowser()` | func | public | `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:62-62` | — | — |
| `URLComponents.enhancedPercentEncodedQuery` | var | public | `Modules/RSWeb/Sources/RSWeb/URLComponents+RSWeb.swift:16-16` | — | — |
| `URLRequest.addBasicAuthorization(username:password:)` | func | public | `Modules/RSWeb/Sources/RSWeb/URLRequest+RSWeb.swift:13-13` | @discardableResult | — |
| `URLResponse.statusIsOK` | var | public | `Modules/RSWeb/Sources/RSWeb/URLResponse+RSWeb.swift:13-13` | — | — |
| `URLResponse.forcedStatusCode` | var | public | `Modules/RSWeb/Sources/RSWeb/URLResponse+RSWeb.swift:17-17` | — | — |
| `HTTPURLResponse.valueForHTTPHeaderField(_:)` | func | public | `Modules/RSWeb/Sources/RSWeb/URLResponse+RSWeb.swift:30-30` | — | — |
| `UserAgentStyle` | enum | public | `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:12-12` | — | — |
| `UserAgent` | struct | public | `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:24-24` | — | — |
| `UserAgent.browserUserAgent` | var | public | `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:31-31` | @MainActor | — |
| `UserAgent.fromInfoPlist()` | func | public | `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:33-33` | — | — |
| `UserAgent.headers()` | func | public | `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:38-38` | — | — |
| `TestingURLProtocol` | class | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:11-11` | — | — |
| `TestingURLProtocol.Response` | struct | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:14-14` | — | — |
| `TestingURLProtocol.Response.statusCode` | var | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:15-15` | — | — |
| `TestingURLProtocol.Response.data` | var | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:16-16` | — | — |
| `TestingURLProtocol.Response.init(statusCode:data:)` | init | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:18-18` | — | — |
| `TestingURLProtocol.currentTestID` | var | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:27-27` | @TaskLocal | — |
| `TestingURLProtocol.testIDHeaderField` | let | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:30-30` | — | — |
| `TestingURLProtocol.setResponse(_:forURLContaining:httpMethod:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:59-59` | — | — |
| `TestingURLProtocol.requestCount(forURLContaining:httpMethod:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:68-68` | — | — |
| `TestingURLProtocol.reset()` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:85-85` | — | — |
| `TestingURLProtocol.endTest(withID:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:90-90` | — | — |
| `TestingURLProtocol.canInit(with:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:126-126` | — | — |
| `TestingURLProtocol.canonicalRequest(for:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:130-130` | — | — |
| `TestingURLProtocol.startLoading()` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:134-134` | — | — |
| `TestingURLProtocol.stopLoading()` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:155-155` | — | — |
| `WebserviceError` | enum | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:12-12` | — | — |
| `WebserviceError.errorDescription` | var | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:19-19` | — | — |
| `URLSession.makeWebserviceSession()` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:42-42` | — | — |
| `URLSession.cancelAll()` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:73-73` | — | — |
| `URLSession.send(request:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:87-88` | @discardableResult | — |
| `URLSession.send(request:method:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:93-93` | — | — |
| `URLSession.send(request:method:payload:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:100-100` | — | — |
| `URLSession.send(request:resultType:dateDecoding:keyDecoding:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+WebserviceJSON.swift:14-14` | — | — |
| `URLSession.send(request:method:payload:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+WebserviceJSON.swift:25-25` | — | — |
| `URLSession.send(request:method:data:resultType:dateDecoding:keyDecoding:)` | func | public | `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+WebserviceJSON.swift:35-35` | — | — |
| `CredentialsError` | enum | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:12-12` | — | — |
| `CredentialsError.errorDescription` | var | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:24-24` | — | — |
| `CredentialsError.recoverySuggestion` | var | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:50-50` | — | — |
| `CredentialsType` | enum | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:55-55` | — | — |
| `Credentials` | struct | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:66-66` | — | — |
| `Credentials.type` | let | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:67-67` | — | — |
| `Credentials.username` | let | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:68-68` | — | — |
| `Credentials.secret` | let | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:69-69` | — | — |
| `Credentials.init(type:username:secret:)` | init | public | `Modules/Secrets/Sources/Secrets/Credentials.swift:71-71` | — | — |
| `CredentialsManager` | struct | public | `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:15-15` | — | — |
| `CredentialsManager.storeCredentials(_:server:)` | func | public | `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:46-46` | — | — |
| `CredentialsManager.retrieveCredentials(type:server:username:)` | func | public | `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:107-107` | — | — |
| `CredentialsManager.removeCredentials(type:server:username:)` | func | public | `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:158-158` | — | — |
| `SyncDatabase` | actor | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:15-15` | — | — |
| `SyncDatabase.databasePath` | let | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:17-17` | — | — |
| `SyncDatabase.init(databasePath:)` | init | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:21-21` | — | — |
| `SyncDatabase.vacuum()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:32-32` | — | — |
| `SyncDatabase.insertStatuses(_:)` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:36-36` | — | — |
| `SyncDatabase.selectForProcessing(limit:)` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:44-44` | — | — |
| `SyncDatabase.selectPendingCount()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:48-48` | — | — |
| `SyncDatabase.selectPendingReadStatusArticleIDs()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:52-52` | — | — |
| `SyncDatabase.selectPendingStarredStatusArticleIDs()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:56-56` | — | — |
| `SyncDatabase.resetAllSelectedForProcessing()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:60-60` | — | — |
| `SyncDatabase.resetSelectedForProcessing(_:key:)` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:68-68` | — | — |
| `SyncDatabase.deleteSelectedForProcessing(_:key:)` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:76-76` | — | — |
| `SyncDatabaseError` | enum | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabaseError.swift:14-14` | — | — |
| `SyncDatabaseError.errorDescription` | var | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabaseError.swift:18-18` | — | — |
| `SyncStatus` | struct | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:13-13` | — | — |
| `SyncStatus.Key` | enum | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:14-14` | — | — |
| `SyncStatus.Key.init(_:)` | init | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:20-20` | — | — |
| `SyncStatus.articleID` | let | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:30-30` | — | — |
| `SyncStatus.key` | let | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:31-31` | — | — |
| `SyncStatus.flag` | let | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:32-32` | — | — |
| `SyncStatus.selected` | let | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:33-33` | — | — |
| `SyncStatus.init(articleID:key:flag:selected:)` | init | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:35-35` | — | — |
| `SyncStatus.databaseDictionary()` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:42-42` | — | — |
| `SyncStatus.hash(into:)` | func | public | `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:46-46` | — | — |
| `ArticleExtractorState` | enum | public | `Shared/Article Extractor/ArticleExtractor.swift:13-13` | — | — |
| `ArticleExtractorDelegate` | protocol | internal | `Shared/Article Extractor/ArticleExtractor.swift:21-21` | @MainActor | — |
| `ArticleExtractor.init(_:delegate:)` | init | public | `Shared/Article Extractor/ArticleExtractor.swift:35-35` | — | — |
| `ArticleExtractor.process()` | func | public | `Shared/Article Extractor/ArticleExtractor.swift:55-55` | — | — |
| `ArticleExtractor.cancel()` | func | public | `Shared/Article Extractor/ArticleExtractor.swift:111-111` | — | — |
| `ArticleThemeDownloader` | class | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:13-13` | — | — |
| `ArticleThemeDownloader.shared` | let | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:14-14` | — | — |
| `ArticleThemeDownloader.ArticleThemeDownloaderError` | enum | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:16-16` | — | — |
| `ArticleThemeDownloader.ArticleThemeDownloaderError.errorDescription` | var | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:22-22` | — | — |
| `ArticleThemeDownloader.downloadTheme(from:)` | func | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:40-40` | @MainActor | — |
| `ArticleThemeDownloader.handleFile(at:)` | func | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:71-71` | — | — |
| `ArticleThemeDownloader.cleanUp()` | func | public | `Shared/ArticleStyles/ArticleThemeDownloader.swift:144-144` | — | — |
| `ArticleThemePlist` | struct | public | `Shared/ArticleStyles/ArticleThemePlist.swift:11-11` | — | — |
| `ArticleThemePlist.name` | let | public | `Shared/ArticleStyles/ArticleThemePlist.swift:12-12` | — | — |
| `ArticleThemePlist.themeIdentifier` | let | public | `Shared/ArticleStyles/ArticleThemePlist.swift:13-13` | — | — |
| `ArticleThemePlist.creatorHomePage` | let | public | `Shared/ArticleStyles/ArticleThemePlist.swift:14-14` | — | — |
| `ArticleThemePlist.creatorName` | let | public | `Shared/ArticleStyles/ArticleThemePlist.swift:15-15` | — | — |
| `ArticleThemePlist.version` | let | public | `Shared/ArticleStyles/ArticleThemePlist.swift:16-16` | — | — |
| `Notification.Name.ArticleThemeNamesDidChangeNotification` | let | public | `Shared/ArticleStyles/ArticleThemesManager.swift:14-14` | — | — |
| `Notification.Name.CurrentArticleThemeDidChangeNotification` | let | public | `Shared/ArticleStyles/ArticleThemesManager.swift:15-15` | — | — |
| `ArticleThemesManager.folderPath` | let | public | `Shared/ArticleStyles/ArticleThemesManager.swift:20-20` | — | — |
| `Article.pathUserInfo` | var | public | `Shared/Extensions/ArticleUtilities.swift:193-193` | — | — |
| `SmallIconProvider` | protocol | internal | `Shared/Extensions/SmallIconProvider.swift:15-15` | — | — |
| `ExtensionContainer` | protocol | internal | `Shared/ShareExtension/ExtensionContainers.swift:12-12` | — | — |
| `PseudoFeed` | protocol | internal | `Shared/SmartFeeds/PseudoFeed.swift:16-16` | — | yes |
| `PseudoFeed` | protocol | internal | `Shared/SmartFeeds/PseudoFeed.swift:27-27` | — | yes |
| `SmartFeed.defaultReadFilterType` | var | public | `Shared/SmartFeeds/SmartFeed.swift:19-19` | — | — |
| `SmartFeedDelegate` | protocol | internal | `Shared/SmartFeeds/SmartFeedDelegate.swift:15-15` | @MainActor | — |
| `SmartFeedsController.shared` | let | public | `Shared/SmartFeeds/SmartFeedsController.swift:16-16` | — | — |
| `UnreadFeed.defaultReadFilterType` | var | public | `Shared/SmartFeeds/UnreadFeed.swift:26-26` | — | — |
| `NSAppleEventDescriptor.usrfDictionary()` | func | public | `Tests/NetNewsWireTests/ScriptingTests/NSAppleEventDescriptor+UserRecordFields.swift:20-20` | — | — |
| `Provider.Entry` | typealias | public | `Widget/TimelineProvider.swift:66-66` | — | — |
| `WidgetTimelineEntry.date` | let | public | `Widget/TimelineProvider.swift:71-71` | — | — |
| `WidgetTimelineEntry.widgetData` | let | public | `Widget/TimelineProvider.swift:72-72` | — | — |
| `BuildSettingsVerifier.ProcessXcodeprojResult` | enum | public | `buildscripts/VerifyNoBS.swift:27-27` | — | — |
| `BuildSettingsVerifier.Mode` | enum | public | `buildscripts/VerifyNoBS.swift:34-34` | — | — |
| `BuildSettingsVerifier.verify()` | func | public | `buildscripts/VerifyNoBS.swift:119-119` | — | — |
| `Notification.Name.userInterfaceColorPaletteDidUpdate` | let | public | `iOS/AppDefaults.swift:34-34` | — | — |
| `Notification.Name.timelineIconSizeDidChange` | let | public | `iOS/AppDefaults.swift:35-35` | — | — |
| `Notification.Name.timelineNumberOfLinesDidChange` | let | public | `iOS/AppDefaults.swift:36-36` | — | — |
| `SearchBarDelegate` | protocol | internal | `iOS/Article/ArticleSearchBar.swift:11-11` | @objc, @MainActor | — |
| `Notification.Name.FindInArticle` | let | public | `iOS/Article/ArticleViewController.swift:422-422` | — | — |
| `Notification.Name.EndFindInArticle` | let | public | `iOS/Article/ArticleViewController.swift:423-423` | — | — |
| `ImageScrollViewDelegate` | protocol | public | `iOS/Article/ImageScrollView.swift:11-11` | @objc | — |
| `ImageScrollView` | class | open | `iOS/Article/ImageScrollView.swift:16-16` | — | — |
| `ImageScrollView.ScaleMode` | enum | public | `iOS/Article/ImageScrollView.swift:18-18` | @objc | — |
| `ImageScrollView.Offset` | enum | public | `iOS/Article/ImageScrollView.swift:25-25` | @objc | — |
| `ImageScrollView.imageContentMode` | var | open | `iOS/Article/ImageScrollView.swift:32-32` | @objc | — |
| `ImageScrollView.initialOffset` | var | open | `iOS/Article/ImageScrollView.swift:33-33` | @objc | — |
| `ImageScrollView.zoomView` | var | public | `iOS/Article/ImageScrollView.swift:35-35` | @objc | — |
| `ImageScrollView.imageScrollViewDelegate` | var | open | `iOS/Article/ImageScrollView.swift:37-37` | @objc | — |
| `ImageScrollView.frame` | var | open | `iOS/Article/ImageScrollView.swift:48-48` | — | — |
| `ImageScrollView.init(frame:)` | init | public | `iOS/Article/ImageScrollView.swift:62-62` | — | — |
| `ImageScrollView.init(coder:)` | init | public | `iOS/Article/ImageScrollView.swift:68-68` | — | — |
| `ImageScrollView.adjustFrameToCenter()` | func | public | `iOS/Article/ImageScrollView.swift:82-82` | @objc | — |
| `ImageScrollView.setup()` | func | open | `iOS/Article/ImageScrollView.swift:158-158` | — | — |
| `ImageScrollView.display(image:)` | func | open | `iOS/Article/ImageScrollView.swift:171-171` | @objc | — |
| `ImageScrollView.refresh()` | func | open | `iOS/Article/ImageScrollView.swift:293-293` | — | — |
| `ImageScrollView.resize()` | func | open | `iOS/Article/ImageScrollView.swift:299-299` | — | — |
| `ImageScrollView.scrollViewDidScroll(_:)` | func | public | `iOS/Article/ImageScrollView.swift:306-306` | — | — |
| `ImageScrollView.scrollViewWillBeginDragging(_:)` | func | public | `iOS/Article/ImageScrollView.swift:310-310` | — | — |
| `ImageScrollView.scrollViewWillEndDragging(_:withVelocity:targetContentOffset:)` | func | public | `iOS/Article/ImageScrollView.swift:314-314` | — | — |
| `ImageScrollView.scrollViewDidEndDragging(_:willDecelerate:)` | func | public | `iOS/Article/ImageScrollView.swift:318-318` | — | — |
| `ImageScrollView.scrollViewWillBeginDecelerating(_:)` | func | public | `iOS/Article/ImageScrollView.swift:322-322` | — | — |
| `ImageScrollView.scrollViewDidEndDecelerating(_:)` | func | public | `iOS/Article/ImageScrollView.swift:326-326` | — | — |
| `ImageScrollView.scrollViewDidEndScrollingAnimation(_:)` | func | public | `iOS/Article/ImageScrollView.swift:330-330` | — | — |
| `ImageScrollView.scrollViewWillBeginZooming(_:with:)` | func | public | `iOS/Article/ImageScrollView.swift:334-334` | — | — |
| `ImageScrollView.scrollViewDidEndZooming(_:with:atScale:)` | func | public | `iOS/Article/ImageScrollView.swift:338-338` | — | — |
| `ImageScrollView.scrollViewShouldScrollToTop(_:)` | func | public | `iOS/Article/ImageScrollView.swift:342-342` | — | — |
| `ImageScrollView.scrollViewDidChangeAdjustedContentInset(_:)` | func | public | `iOS/Article/ImageScrollView.swift:346-347` | @available | — |
| `ImageScrollView.viewForZooming(in:)` | func | public | `iOS/Article/ImageScrollView.swift:351-351` | — | — |
| `ImageScrollView.scrollViewDidZoom(_:)` | func | public | `iOS/Article/ImageScrollView.swift:355-355` | — | — |
| `WebViewControllerDelegate` | protocol | internal | `iOS/Article/WebViewController.swift:19-19` | @MainActor | — |
| `ErrorHandler.present(_:)` | func | public | `iOS/ErrorHandler.swift:17-17` | @Sendable | — |
| `ErrorHandler.log(_:)` | func | public | `iOS/ErrorHandler.swift:29-29` | @Sendable | — |
| `MainFeedCollectionHeaderReusableViewDelegate` | protocol | internal | `iOS/MainFeed/Collection View Cells/MainFeedCollectionHeaderReusableView.swift:12-12` | @MainActor | — |
| `MainFeedCollectionViewFolderCellDelegate` | protocol | internal | `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewFolderCell.swift:12-12` | @MainActor | — |
| `MainTimelineCellLayout` | protocol | internal | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:13-13` | @MainActor | — |
| `MarkAsReadAlertControllerSourceType` | protocol | internal | `iOS/MainTimeline/MarkAsReadAlertController.swift:12-12` | — | — |
| `AboutContributor` | struct | public | `iOS/Settings/AboutContributor.swift:11-11` | — | — |
| `AboutContributor.id` | let | public | `iOS/Settings/AboutContributor.swift:12-12` | — | — |
| `Contributors` | enum | public | `iOS/Settings/AboutContributor.swift:18-18` | — | — |
| `Contributors.contributor` | var | public | `iOS/Settings/AboutContributor.swift:35-35` | — | — |
| `ShareFolderPickerControllerDelegate` | protocol | internal | `iOS/ShareExtension/ShareFolderPickerController.swift:13-13` | @MainActor | — |
| `UIActivityViewController.init(url:title:applicationActivities:)` | init | public | `iOS/UIKit Extensions/UIActivityViewController+Extras.swift:15-15` | — | yes |

## Protocol requirements

| requirement | protocol | kind | declared at |
|---|---|---|---|
| `objects` | `Inspector` | var | `Mac/Inspector/InspectorWindowController.swift:12-12` |
| `isFallbackInspector` | `Inspector` | var | `Mac/Inspector/InspectorWindowController.swift:13-13` |
| `windowTitle` | `Inspector` | var | `Mac/Inspector/InspectorWindowController.swift:14-14` |
| `canInspect(_:)` | `Inspector` | func | `Mac/Inspector/InspectorWindowController.swift:16-16` |
| `addFeedWindowController(_:userEnteredURL:userEnteredTitle:container:)` | `AddFeedWindowControllerDelegate` | func | `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:17-17` |
| `addFeedWindowControllerUserDidCancel(_:)` | `AddFeedWindowControllerDelegate` | func | `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:18-18` |
| `mouseDidEnter(_:link:)` | `DetailWebViewControllerDelegate` | func | `Mac/MainWindow/Detail/DetailWebViewController.swift:17-17` |
| `mouseDidExit(_:)` | `DetailWebViewControllerDelegate` | func | `Mac/MainWindow/Detail/DetailWebViewController.swift:18-18` |
| `renameWindowController(_:didRenameObject:withNewName:)` | `RenameWindowControllerDelegate` | func | `Mac/MainWindow/Sidebar/Renaming/RenameWindowController.swift:13-13` |
| `sidebarSelectionDidChange(_:selectedObjects:)` | `SidebarDelegate` | func | `Mac/MainWindow/Sidebar/SidebarViewController.swift:21-21` |
| `unreadCount(for:)` | `SidebarDelegate` | func | `Mac/MainWindow/Sidebar/SidebarViewController.swift:22-22` |
| `sidebarInvalidatedRestorationState(_:)` | `SidebarDelegate` | func | `Mac/MainWindow/Sidebar/SidebarViewController.swift:23-23` |
| `timelineSelectionDidChange(_:articles:mode:)` | `TimelineContainerViewControllerDelegate` | func | `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:14-14` |
| `timelineRequestedFeedSelection(_:feed:)` | `TimelineContainerViewControllerDelegate` | func | `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:15-15` |
| `timelineInvalidatedRestorationState(_:)` | `TimelineContainerViewControllerDelegate` | func | `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:16-16` |
| `timelineSelectionDidChange(_:selectedArticles:)` | `TimelineDelegate` | func | `Mac/MainWindow/Timeline/TimelineViewController.swift:17-17` |
| `timelineRequestedFeedSelection(_:feed:)` | `TimelineDelegate` | func | `Mac/MainWindow/Timeline/TimelineViewController.swift:18-18` |
| `timelineInvalidatedRestorationState(_:)` | `TimelineDelegate` | func | `Mac/MainWindow/Timeline/TimelineViewController.swift:19-19` |
| `timelineRequestedSortChange(_:parameters:)` | `TimelineDelegate` | func | `Mac/MainWindow/Timeline/TimelineViewController.swift:20-20` |
| `presentSheetForAccount(_:)` | `AccountsPreferencesAddAccountDelegate` | func | `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:16-16` |
| `installAppleEventHandlers()` | `AppDelegateAppleEvents` | func | `Mac/Scripting/AppDelegate+Scriptability.swift:24-24` |
| `getURL(_:_:)` | `AppDelegateAppleEvents` | func | `Mac/Scripting/AppDelegate+Scriptability.swift:25-25` |
| `scriptingCurrentArticle` | `ScriptingAppDelegate` | var | `Mac/Scripting/AppDelegate+Scriptability.swift:29-29` |
| `scriptingSelectedArticles` | `ScriptingAppDelegate` | var | `Mac/Scripting/AppDelegate+Scriptability.swift:30-30` |
| `scriptingSelectedFeeds` | `ScriptingAppDelegate` | var | `Mac/Scripting/AppDelegate+Scriptability.swift:31-31` |
| `scriptingMainWindowController` | `ScriptingAppDelegate` | var | `Mac/Scripting/AppDelegate+Scriptability.swift:32-32` |
| `scriptingCurrentArticle` | `ScriptingMainWindowController` | var | `Mac/Scripting/MainWindowController+Scriptability.swift:14-14` |
| `scriptingSelectedArticles` | `ScriptingMainWindowController` | var | `Mac/Scripting/MainWindowController+Scriptability.swift:15-15` |
| `scriptingSelectedFeeds` | `ScriptingMainWindowController` | var | `Mac/Scripting/MainWindowController+Scriptability.swift:16-16` |
| `objectSpecifier` | `ScriptingObject` | var | `Mac/Scripting/ScriptingObject.swift:12-12` |
| `scriptingKey` | `ScriptingObject` | var | `Mac/Scripting/ScriptingObject.swift:13-13` |
| `name` | `NamedScriptingObject` | var | `Mac/Scripting/ScriptingObject.swift:17-17` |
| `scriptingUniqueID` | `UniqueIDScriptingObject` | var | `Mac/Scripting/ScriptingObject.swift:21-21` |
| `scriptingClassDescription` | `ScriptingObjectContainer` | var | `Mac/Scripting/ScriptingObjectContainer.swift:13-13` |
| `deleteElement(_:)` | `ScriptingObjectContainer` | func | `Mac/Scripting/ScriptingObjectContainer.swift:14-14` |
| `account` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:20-20` |
| `behaviors` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:22-22` |
| `isOPMLImportInProgress` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:24-24` |
| `server` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:26-26` |
| `credentials` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:27-27` |
| `accountSettings` | `AccountDelegate` | var | `Modules/Account/Sources/Account/AccountDelegate.swift:28-28` |
| `receiveRemoteNotification(userInfo:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:30-30` |
| `refreshAll()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:32-32` |
| `syncArticleStatus()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:35-35` |
| `sendArticleStatus()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:36-36` |
| `refreshArticleStatus()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:37-37` |
| `importOPML(opmlFile:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:39-39` |
| `createFolder(name:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:41-41` |
| `renameFolder(with:to:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:42-42` |
| `removeFolder(with:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:43-43` |
| `createFeed(url:name:container:validateFeed:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:45-45` |
| `renameFeed(with:to:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:46-46` |
| `addFeed(feed:container:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:47-47` |
| `removeFeed(feed:container:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:48-48` |
| `moveFeed(feed:sourceContainer:destinationContainer:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:49-49` |
| `restoreFeed(feed:container:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:51-51` |
| `restoreFolder(folder:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:52-52` |
| `markArticles(articleIDs:statusKey:flag:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:54-54` |
| `accountDidInitialize()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:57-57` |
| `accountWillBeDeleted()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:59-59` |
| `validateCredentials(credentials:endpoint:)` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:61-61` |
| `vacuumDatabases()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:63-63` |
| `suspendNetwork()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:66-66` |
| `resume()` | `AccountDelegate` | func | `Modules/Account/Sources/Account/AccountDelegate.swift:69-69` |
| `fetchArticles()` | `ArticleFetcher` | func | `Modules/Account/Sources/Account/ArticleFetcher.swift:14-14` |
| `fetchArticlesAsync()` | `ArticleFetcher` | func | `Modules/Account/Sources/Account/ArticleFetcher.swift:15-15` |
| `fetchUnreadArticles()` | `ArticleFetcher` | func | `Modules/Account/Sources/Account/ArticleFetcher.swift:16-16` |
| `fetchUnreadArticlesAsync()` | `ArticleFetcher` | func | `Modules/Account/Sources/Account/ArticleFetcher.swift:17-17` |
| `account` | `Container` | var | `Modules/Account/Sources/Account/Container.swift:18-18` |
| `topLevelFeeds` | `Container` | var | `Modules/Account/Sources/Account/Container.swift:19-19` |
| `folders` | `Container` | var | `Modules/Account/Sources/Account/Container.swift:20-20` |
| `externalID` | `Container` | var | `Modules/Account/Sources/Account/Container.swift:21-21` |
| `hasAtLeastOneFeed()` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:23-23` |
| `objectIsChild(_:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:24-24` |
| `hasChildFolder(with:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:26-26` |
| `childFolder(with:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:27-27` |
| `removeFeedFromTreeAtTopLevel(_:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:29-29` |
| `addFeedToTreeAtTopLevel(_:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:30-30` |
| `flattenedFeeds()` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:33-33` |
| `has(_:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:34-34` |
| `hasFeed(with:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:35-35` |
| `hasFeed(withURL:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:36-36` |
| `existingFeed(withFeedID:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:37-37` |
| `existingFeed(withURL:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:38-38` |
| `existingFeed(withExternalID:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:39-39` |
| `existingFolder(with:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:40-40` |
| `existingFolder(withID:)` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:41-41` |
| `postChildrenDidChangeNotification()` | `Container` | func | `Modules/Account/Sources/Account/Container.swift:43-43` |
| `containerID` | `ContainerIdentifiable` | var | `Modules/Account/Sources/Account/ContainerIdentifier.swift:12-12` |
| `reauthorizeFeedlyAPICaller()` | `FeedlyAPICallerDelegate` | func | `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:19-19` |
| `id` | `FeedlyResourceID` | var | `Modules/Account/Sources/Account/Feedly/FeedlyModel.swift:325-325` |
| `oauthAccountAuthorizationOperation(_:didCreate:)` | `OAuthAccountAuthorizationOperationDelegate` | func | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:16-16` |
| `oauthAccountAuthorizationOperation(_:didFailWith:)` | `OAuthAccountAuthorizationOperationDelegate` | func | `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:17-17` |
| `accessToken` | `OAuthAccessTokenResponse` | var | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:157-157` |
| `tokenType` | `OAuthAccessTokenResponse` | var | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:158-158` |
| `expiresIn` | `OAuthAccessTokenResponse` | var | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:159-159` |
| `refreshToken` | `OAuthAccessTokenResponse` | var | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:160-160` |
| `scope` | `OAuthAccessTokenResponse` | var | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:161-161` |
| `oauthAuthorizationCodeGrantRequest(state:)` | `OAuthAuthorizationGranting` | func | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:174-174` |
| `requestOAuthAccessToken(with:)` | `OAuthAuthorizationGranting` | func | `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:176-176` |
| `localAccountRefresher(_:articleChanges:)` | `LocalAccountRefresherDelegate` | func | `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:20-20` |
| `account` | `SidebarItem` | var | `Modules/Account/Sources/Account/SidebarItem.swift:19-19` |
| `defaultReadFilterType` | `SidebarItem` | var | `Modules/Account/Sources/Account/SidebarItem.swift:20-20` |
| `sidebarItemID` | `SidebarItemIdentifiable` | var | `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:12-12` |
| `unreadCount` | `UnreadCountProvider` | var | `Modules/Account/Sources/Account/UnreadCountProvider.swift:17-17` |
| `postUnreadCountDidChangeNotification()` | `UnreadCountProvider` | func | `Modules/Account/Sources/Account/UnreadCountProvider.swift:19-19` |
| `calculateUnreadCount(_:)` | `UnreadCountProvider` | func | `Modules/Account/Sources/Account/UnreadCountProvider.swift:20-20` |
| `cloudKitDidModify(changed:deleted:)` | `CloudKitZoneDelegate` | func | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:44-44` |
| `qualityOfService` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:54-54` |
| `zoneID` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:56-56` |
| `container` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:58-58` |
| `database` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:59-59` |
| `delegate` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:60-60` |
| `fetchChangesPageHandler` | `CloudKitZone` | var | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:63-63` |
| `resetChangeToken()` | `CloudKitZone` | func | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:66-66` |
| `generateRecordID()` | `CloudKitZone` | func | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:69-69` |
| `subscribeToZoneChanges()` | `CloudKitZone` | func | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:72-72` |
| `receiveRemoteNotification(userInfo:)` | `CloudKitZone` | func | `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:75-75` |
| `asData` | `NewsBlurDataConvertible` | var | `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:13-13` |
| `keydown(_:in:)` | `KeyboardDelegate` | func | `Modules/RSCore/Sources/RSCore/AppKit/KeyboardDelegateProtocol.swift:14-14` |
| `pasteboardWriter` | `PasteboardWriterOwner` | var | `Modules/RSCore/Sources/RSCore/AppKit/PasteboardWriterOwner.swift:13-13` |
| `dateCreated` | `CacheRecord` | var | `Modules/RSCore/Sources/RSCore/Cache.swift:12-12` |
| `nameForDisplay` | `DisplayNameProvider` | var | `Modules/RSCore/Sources/RSCore/DisplayNameProvider.swift:18-18` |
| `OPMLString(indentLevel:allowCustomAttributes:)` | `OPMLRepresentable` | func | `Modules/RSCore/Sources/RSCore/OPMLRepresentable.swift:13-13` |
| `progressInfo` | `ProgressInfoReporter` | var | `Modules/RSCore/Sources/RSCore/RSProgress.swift:44-44` |
| `rename(to:completion:)` | `Renamable` | func | `Modules/RSCore/Sources/RSCore/Renamable.swift:19-19` |
| `title` | `SendToCommand` | var | `Modules/RSCore/Sources/RSCore/SendToCommand.swift:27-27` |
| `image` | `SendToCommand` | var | `Modules/RSCore/Sources/RSCore/SendToCommand.swift:31-31` |
| `canSendObject(_:selectedText:)` | `SendToCommand` | func | `Modules/RSCore/Sources/RSCore/SendToCommand.swift:39-39` |
| `sendObject(_:selectedText:)` | `SendToCommand` | func | `Modules/RSCore/Sources/RSCore/SendToCommand.swift:46-46` |
| `undoActionName` | `UndoableCommand` | var | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:12-12` |
| `redoActionName` | `UndoableCommand` | var | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:13-13` |
| `undoManager` | `UndoableCommand` | var | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:14-14` |
| `perform()` | `UndoableCommand` | func | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:16-16` |
| `undo()` | `UndoableCommand` | func | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:17-17` |
| `undoableCommands` | `UndoableCommandRunner` | var | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:40-40` |
| `undoManager` | `UndoableCommandRunner` | var | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:41-41` |
| `runCommand(_:)` | `UndoableCommandRunner` | func | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:43-43` |
| `clearUndoableCommands()` | `UndoableCommandRunner` | func | `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:44-44` |
| `name` | `DatabaseTable` | var | `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:14-14` |
| `htmlScanner(_:didStartTag:attributes:selfClosing:)` | `HTMLScannerDelegate` | func | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:483-483` |
| `htmlScanner(_:didEndTag:)` | `HTMLScannerDelegate` | func | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:489-489` |
| `htmlScanner(_:didFindCharacters:)` | `HTMLScannerDelegate` | func | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:493-493` |
| `htmlScannerDidEnd(_:)` | `HTMLScannerDelegate` | func | `Modules/RSParser/Sources/RSParser/HTML/HTMLScanner.swift:497-497` |
| `xmlSAXParser(_:didStartElement:namespace:attributes:)` | `XMLSAXParserDelegate` | func | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:23-23` |
| `xmlSAXParser(_:didEndElement:namespace:)` | `XMLSAXParserDelegate` | func | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:29-29` |
| `xmlSAXParser(_:didFindCharacters:)` | `XMLSAXParserDelegate` | func | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:35-35` |
| `xmlSAXParser(_:didCaptureRawInnerContent:forElement:namespace:)` | `XMLSAXParserDelegate` | func | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:51-51` |
| `xmlSAXParserDidEnd(_:)` | `XMLSAXParserDelegate` | func | `Modules/RSParser/Sources/RSParser/XML/XMLSAXParserDelegate.swift:57-57` |
| `treeController(treeController:childNodesFor:)` | `TreeControllerDelegate` | func | `Modules/RSTree/Sources/RSTree/TreeController.swift:12-12` |
| `downloadSession(_:conditionalGetInfoFor:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:18-18` |
| `downloadSession(_:didReceiveResponse:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:19-19` |
| `downloadSession(_:didSkip:reason:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:20-20` |
| `downloadSession(_:downloadDidComplete:response:data:error:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:21-21` |
| `downloadSession(_:shouldContinueAfterReceivingData:url:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:22-22` |
| `downloadSession(_:httpError:url:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:23-23` |
| `downloadSession(_:didFollowRedirectFor:from:to:statusCode:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:24-24` |
| `downloadSessionDidComplete(_:)` | `DownloadSessionDelegate` | func | `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:25-25` |
| `articleExtractionDidFail(with:)` | `ArticleExtractorDelegate` | func | `Shared/Article Extractor/ArticleExtractor.swift:22-22` |
| `articleExtractionDidComplete(extractedArticle:)` | `ArticleExtractorDelegate` | func | `Shared/Article Extractor/ArticleExtractor.swift:23-23` |
| `smallIcon` | `SmallIconProvider` | var | `Shared/Extensions/SmallIconProvider.swift:16-16` |
| `name` | `ExtensionContainer` | var | `Shared/ShareExtension/ExtensionContainers.swift:13-13` |
| `accountID` | `ExtensionContainer` | var | `Shared/ShareExtension/ExtensionContainers.swift:14-14` |
| `containerID` | `ExtensionContainer` | var | `Shared/ShareExtension/ExtensionContainers.swift:15-15` |
| `fetchType` | `SmartFeedDelegate` | var | `Shared/SmartFeeds/SmartFeedDelegate.swift:16-16` |
| `fetchUnreadCount(account:)` | `SmartFeedDelegate` | func | `Shared/SmartFeeds/SmartFeedDelegate.swift:17-17` |
| `nextWasPressed(_:)` | `SearchBarDelegate` | func | `iOS/Article/ArticleSearchBar.swift:12-12` |
| `previousWasPressed(_:)` | `SearchBarDelegate` | func | `iOS/Article/ArticleSearchBar.swift:13-13` |
| `doneWasPressed(_:)` | `SearchBarDelegate` | func | `iOS/Article/ArticleSearchBar.swift:14-14` |
| `searchBar(_:textDidChange:)` | `SearchBarDelegate` | func | `iOS/Article/ArticleSearchBar.swift:15-15` |
| `imageScrollViewDidGestureSwipeUp(imageScrollView:)` | `ImageScrollViewDelegate` | func | `iOS/Article/ImageScrollView.swift:12-12` |
| `imageScrollViewDidGestureSwipeDown(imageScrollView:)` | `ImageScrollViewDelegate` | func | `iOS/Article/ImageScrollView.swift:13-13` |
| `webViewController(_:articleExtractorButtonStateDidUpdate:)` | `WebViewControllerDelegate` | func | `iOS/Article/WebViewController.swift:20-20` |
| `mainFeedCollectionHeaderReusableViewDidTapDisclosureIndicator(_:)` | `MainFeedCollectionHeaderReusableViewDelegate` | func | `iOS/MainFeed/Collection View Cells/MainFeedCollectionHeaderReusableView.swift:13-13` |
| `mainFeedCollectionFolderViewCellDisclosureDidToggle(_:expanding:)` | `MainFeedCollectionViewFolderCellDelegate` | func | `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewFolderCell.swift:13-13` |
| `height` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:14-14` |
| `unreadIndicatorRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:15-15` |
| `starRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:16-16` |
| `iconImageRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:17-17` |
| `titleRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:18-18` |
| `summaryRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:19-19` |
| `feedNameRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:20-20` |
| `dateRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:21-21` |
| `separatorRect` | `MainTimelineCellLayout` | var | `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:22-22` |
| `shareFolderPickerDidSelect(_:)` | `ShareFolderPickerControllerDelegate` | func | `iOS/ShareExtension/ShareFolderPickerController.swift:14-14` |

## Products

| product | product kind | container | declared at |
|---|---|---|---|
| `Account` | library | `Modules/Account/Package.swift` | `Modules/Account/Package.swift:8-9` |
| `ActivityLog` | library | `Modules/ActivityLog/Package.swift` | `Modules/ActivityLog/Package.swift:9-10` |
| `Articles` | library | `Modules/Articles/Package.swift` | `Modules/Articles/Package.swift:8-9` |
| `ArticlesDatabase` | library | `Modules/ArticlesDatabase/Package.swift` | `Modules/ArticlesDatabase/Package.swift:8-9` |
| `CloudKitSync` | library | `Modules/CloudKitSync/Package.swift` | `Modules/CloudKitSync/Package.swift:8-9` |
| `ErrorLog` | library | `Modules/ErrorLog/Package.swift` | `Modules/ErrorLog/Package.swift:8-9` |
| `FeedFinder` | library | `Modules/FeedFinder/Package.swift` | `Modules/FeedFinder/Package.swift:8-9` |
| `HTMLMetadata` | library | `Modules/HTMLMetadata/Package.swift` | `Modules/HTMLMetadata/Package.swift:8-9` |
| `Images` | library | `Modules/Images/Package.swift` | `Modules/Images/Package.swift:8-9` |
| `NewsBlur` | library | `Modules/NewsBlur/Package.swift` | `Modules/NewsBlur/Package.swift:8-9` |
| `RSCore` | library | `Modules/RSCore/Package.swift` | `Modules/RSCore/Package.swift:8-8` |
| `RSCoreObjC` | library | `Modules/RSCore/Package.swift` | `Modules/RSCore/Package.swift:9-9` |
| `RSCoreResources` | library | `Modules/RSCore/Package.swift` | `Modules/RSCore/Package.swift:10-10` |
| `RSDatabase` | library | `Modules/RSDatabase/Package.swift` | `Modules/RSDatabase/Package.swift:8-9` |
| `RSDatabaseObjC` | library | `Modules/RSDatabase/Package.swift` | `Modules/RSDatabase/Package.swift:12-13` |
| `RSParser` | library | `Modules/RSParser/Package.swift` | `Modules/RSParser/Package.swift:8-9` |
| `RSTree` | library | `Modules/RSTree/Package.swift` | `Modules/RSTree/Package.swift:8-9` |
| `RSWeb` | library | `Modules/RSWeb/Package.swift` | `Modules/RSWeb/Package.swift:8-9` |
| `Secrets` | library | `Modules/Secrets/Package.swift` | `Modules/Secrets/Package.swift:8-9` |
| `SyncDatabase` | library | `Modules/SyncDatabase/Package.swift` | `Modules/SyncDatabase/Package.swift:8-9` |

## @main declarations

| @main type | kind | owning target | declared at |
|---|---|---|---|
| `AppDelegate` | class | `NetNewsWire (NetNewsWire.xcodeproj)` | `Mac/AppDelegate.swift:30-31` |
| `NetNewsWireWidgets` | struct | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | `Widget/WidgetBundle.swift:91-92` |
| `AppDelegate` | class | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `iOS/AppDelegate.swift:23-24` |

## Residuals

- `parse-error` `Mac/About/AboutWindowController.swift` lines 57-57 — location declaration header; effect enclosing var version
- `parse-error` `Mac/About/AboutWindowController.swift` lines 58-58 — location declaration header; effect enclosing var build
- `parse-error` `Mac/MainWindow/MainWindowController.swift` lines 1384-1384 — location body; effect enclosing func restoreLegacyState
- `parse-error` `Mac/MainWindow/MainWindowController.swift` lines 1733-1733 — location body; effect enclosing func restoreLegacySplitViewState
- `parse-error` `Mac/MainWindow/NNW3/NNW3Document.swift` lines 83-83 — location body; effect enclosing func itemsWithPlist
- `parse-error` `Mac/SafariExtension/SafariExtensionHandler.swift` lines 30-30 — location body; effect enclosing func validateToolbarItem
- `parse-error` `Mac/Scripting/Folder+Scriptability.swift` lines 71-71 — location declaration header; effect enclosing var name
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 529-529 — location body; effect enclosing func importOPML
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 687-687 — location body; effect enclosing func addFeed
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 732-732 — location body; effect enclosing func removeFeed
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 743-743 — location body; effect enclosing func moveFeed
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 758-758 — location body; effect enclosing func restoreFeed
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 774-774 — location body; effect enclosing func removeFolder
- `parse-error` `Modules/Account/Sources/Account/Account.swift` lines 789-789 — location body; effect enclosing func restoreFolder
- `parse-error` `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift` lines 245-245 — location body; effect enclosing func refreshArticleStatus
- `parse-error` `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift` lines 33-33 — location declaration header; effect enclosing var starredValue
- `parse-error` `Modules/Account/Sources/Account/Feed.swift` lines 217-217 — location body; effect enclosing func rename
- `parse-error` `Modules/Account/Sources/Account/FeedSettingsDatabase.swift` lines 119-119 — location body; effect enclosing func insertRow
- `parse-error` `Modules/Account/Sources/Account/FeedSettingsImporter.swift` lines 55-55 — location body; effect enclosing func importFeed
- `parse-error` `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift` lines 545-545 — location body; effect enclosing func checkImportResult
- `parse-error` `Modules/Account/Sources/Account/Folder.swift` lines 68-68 — location body; effect enclosing func rename
- `parse-error` `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift` lines 175-176 — location body; effect enclosing func refreshAll
- `parse-error` `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift` lines 181-181 — location body; effect enclosing func refreshAll
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/AccountOPMLLoadTests.swift` lines 16-16, 30-30, 43-43 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/FeedSettingsDatabaseTests.swift` lines 14-14, 25-25 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedbin/FeedbinFeedNameTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedbin/FeedbinFeedNameTests.swift` lines 18-18 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift` lines 17-17, 46-46 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedly/FeedlyActivityMessageTests.swift` lines 14-14, 20-20, 25-25, 30-30, 35-35, 43-43, 48-48 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedly/FeedlyFeedNameTests.swift` lines 15-15, 28-28, 41-41 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift` lines 14-14 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift` lines 20-20, 44-44 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/Feedly/FeedlyUnmarkableArticleIDsTests.swift` lines 16-16, 22-22, 28-28, 33-33 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTraitTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTraitTests.swift` lines 16-16, 20-20 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/NewsBlur/NewsBlurFeedNameTests.swift` lines 17-17, 30-30 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Account/Tests/AccountTests/ReaderAPI/ReaderAPIEntryTests.swift` lines 14-14, 19-19, 26-26, 31-31, 37-37, 42-42 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ActivityLog/Tests/ActivityLogTests/ActivityLogTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ActivityLog/Tests/ActivityLogTests/ActivityLogTests.swift` lines 14-14, 24-24, 34-34, 47-47, 62-62, 81-81, 103-103, 121-121, 135-135, 148-148, 165-165, 181-181, 191-191, 203-203, 216-216, 233-233, 247-247, 259-259, 271-271, 288-288, 301-301, 324-324, 332-332, 345-345, 359-359, 367-367, 371-371, 377-377, 381-381, 386-386, 391-391 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Articles/Tests/ArticlesTests/AuthorCacheTests.swift` lines 13-13, 54-54 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/Articles/Tests/ArticlesTests/AuthorCacheTests.swift` lines 15-15, 26-26, 35-35, 44-44, 60-60 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 136-136 — location body; effect enclosing func fetchArticlesMatching
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 646-646 — location body; effect enclosing func fetchArticles
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 655-655 — location body; effect enclosing func fetchArticlesCount
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift` lines 179-179 — location body; effect enclosing func fetchArticleIDs
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift` lines 20-20 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift` lines 30-30, 41-41, 54-54, 71-71 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift` lines 17-17 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift` lines 26-26, 42-42, 57-57, 70-70, 79-79, 95-95, 108-108 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift` lines 17-17 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift` lines 31-31, 36-36, 42-42, 47-47, 53-53, 60-60, 67-67, 75-75 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 154-154 — location body; effect enclosing func createZoneRecord
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 389-389 — location body; effect enclosing func saveIfNew
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 390-441 — location body; effect enclosing func saveIfNew
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 514-514 — location body; effect enclosing func delete
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 612-612 — location body; effect enclosing func delete
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 632-632 — location body; effect enclosing func modify
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 650-650 — location body; effect enclosing func modify
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 651-730 — location body; effect enclosing func modify
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 805-805 — location body; effect enclosing func fetchChangesInZone
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 823-823 — location body; effect enclosing func fetchChangesInZone
- `parse-error` `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift` lines 879-879 — location body; effect enclosing func queryPaginated
- `declaration-recovered` `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift` lines 13-67 — location top level; actor ErrorLogDatabase dropped by a top-level error, recovered from lines 13-47
- `parse-error` `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift` lines 1-63 — location top level; effect no enclosing declaration
- `macro-not-expanded` `Modules/ErrorLog/Tests/ErrorLogTests/ErrorLogDatabaseTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/ErrorLog/Tests/ErrorLogTests/ErrorLogDatabaseTests.swift` lines 26-26, 47-47, 65-65 — attached macro @Test is not expanded; code it generates does not render
- `conditional-declaration` `Modules/Images/Sources/Images/ColorHash.swift` lines 63-73 — ColorHash.color is declared in 2 `#if` branches; every branch renders and none is evaluated
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 127-127 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 128-128 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 129-129 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 130-130 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 131-131 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/Images/Sources/Images/ImageMetadataDatabase.swift` lines 132-132 — location body; effect enclosing func loadCachesFromDatabase
- `parse-error` `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift` lines 133-133 — location body; effect enclosing init
- `parse-error` `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift` lines 134-134 — location body; effect enclosing init
- `parse-error` `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift` lines 135-135 — location body; effect enclosing init
- `parse-error` `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift` lines 136-136 — location body; effect enclosing init
- `parse-error` `Modules/RSCore/Sources/RSCore/AppKit/RSAppMovementMonitor.swift` lines 49-49 — location declaration header; effect enclosing var appName
- `parse-error` `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift` lines 14-14 — location declaration header; effect enclosing var mutex
- `parse-error` `Modules/RSCore/Sources/RSCore/NotificationCenter+RSCore.swift` lines 13-13 — location body; effect enclosing func postOnMainThread
- `parse-error` `Modules/RSCore/Sources/RSCore/NotificationCenter+RSCore.swift` lines 14-14 — location body; effect enclosing func postOnMainThread
- `conditional-declaration` `Modules/RSCore/Sources/RSCore/RSImage.swift` lines 13-17, 19-23 — RSColor is declared in 2 `#if` branches; every branch renders and none is evaluated
- `conditional-declaration` `Modules/RSCore/Sources/RSCore/RSImage.swift` lines 13-17, 19-23 — RSImage is declared in 2 `#if` branches; every branch renders and none is evaluated
- `conditional-declaration` `Modules/RSCore/Sources/RSCore/RSScreen.swift` lines 9-19, 21-28 — RSScreen is declared in 2 `#if` branches; every branch renders and none is evaluated
- `conditional-declaration` `Modules/RSCore/Sources/RSCore/RSScreen.swift` lines 9-19, 21-28 — RSScreen.maxScreenScale is declared in 2 `#if` branches; every branch renders and none is evaluated
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/CGImageLuminanceTests.swift` lines 15-15 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/CGImageLuminanceTests.swift` lines 17-17, 24-24, 29-29, 34-34, 39-39 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespaceTests.swift` lines 17-17 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespaceTests.swift` lines 21-21, 25-27, 31-31, 37-37, 41-41, 45-45, 51-51, 55-55, 61-71, 80-80, 85-85, 89-89, 95-95 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/HMACTests.swift` lines 11-11 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/HMACTests.swift` lines 13-14, 20-21, 27-28, 36-37, 45-46, 53-54 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/MD5Tests.swift` lines 11-11 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/MD5Tests.swift` lines 13-14, 18-23, 27-28 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 29-29 — location body; effect enclosing func testOperationAndDependency
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 55-55 — location body; effect enclosing func testOperationAndDependencyAddedOutOfOrder
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 80-80 — location body; effect enclosing func testOperationAndTwoDependenciesAddedOutOfOrder
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 115-115 — location body; effect enclosing func testChildOperationWithTwoDependencies
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 152-152 — location body; effect enclosing func testAddingManyOperations
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 190-190 — location body; effect enclosing func testAddingManyOperationsWithCompletionBlocks
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/StripHTMLTests.swift` lines 14-14, 18-18, 22-22, 26-26, 33-33, 37-37, 43-43, 49-49, 55-55, 61-61, 67-67, 79-79, 88-88, 94-94, 103-104, 115-116 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSCore/Tests/RSCoreTests/URL+RSCoreTests.swift` lines 18-18, 23-23, 28-28, 35-35, 40-40 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift` lines 20-21 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift` lines 23-23, 59-59 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift` lines 70-70 — location declaration header; effect enclosing var feedURL
- `parse-error` `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift` lines 75-75 — location body; effect enclosing func parse
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypeTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypeTests.swift` lines 17-24, 31-44, 51-58, 65-65, 72-80, 87-87 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserTests.swift` lines 15-15, 23-23, 29-29, 46-46, 52-52, 58-58, 69-69 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserTests.swift` lines 15-15 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserTests.swift` lines 15-15, 32-32, 73-73, 98-98, 127-127, 149-149, 174-174, 189-189, 212-212, 232-232, 253-253, 275-275, 299-299, 316-316, 336-336, 342-342, 359-359, 377-377, 395-395, 406-406, 435-435, 463-463, 485-485, 511-511, 524-524, 547-547, 567-567, 590-590, 615-615, 641-641 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift` lines 17-17, 24-24, 31-31, 73-73, 104-104, 130-130 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift` lines 43-69 — location member; effect enclosing struct OPMLTests
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserTests.swift` lines 15-15, 21-21, 39-39, 48-48, 59-59, 73-73, 87-87, 99-99, 107-107, 119-119, 129-129, 135-135, 143-143, 151-151, 157-157, 165-165, 173-173, 190-190, 209-209, 221-221, 230-230, 254-254, 285-285, 309-309, 332-332, 345-345, 365-365 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkTests.swift` lines 15-15, 35-35, 58-58, 76-76, 94-94, 111-111, 126-126 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataTests.swift` lines 15-15, 29-29, 42-42, 57-57, 76-76, 84-84, 92-92, 106-106, 122-122, 133-133, 156-156, 175-175, 189-189 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLRelativeURLResolverTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/HTML/HTMLRelativeURLResolverTests.swift` lines 22-22, 37-37, 42-42, 47-47, 54-54, 70-70, 82-82, 90-90, 108-108, 116-116, 124-124, 142-142, 151-151, 177-177 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `parse-error` `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift` lines 37-313 — location member; effect enclosing struct DateParserTests
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingTests.swift` lines 14-15, 23-31, 37-45, 49-49, 58-63, 67-67, 77-77, 83-83, 89-89, 94-94, 100-100, 111-111, 117-117, 123-143, 149-149, 154-154, 160-160, 166-166, 172-172, 187-187, 200-200 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLASCIITests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLASCIITests.swift` lines 20-20, 39-41, 45-48, 54-54, 60-63, 69-69, 78-82, 88-90, 94-96, 100-102, 106-113, 119-119, 138-141, 145-145, 151-156, 162-165, 169-173, 177-181, 185-189, 195-195, 200-200, 206-206, 212-212, 218-218, 228-228, 233-233, 238-238, 243-243, 248-248, 253-253 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLAttributesTests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLAttributesTests.swift` lines 37-37, 42-42, 50-50, 55-55, 60-60, 65-65, 73-73, 78-78, 84-84, 89-89, 95-95, 102-102, 108-108, 116-116, 124-124, 130-130, 139-139, 151-151, 155-155, 167-167, 183-183, 191-191 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift` lines 50-50, 55-55, 59-59, 63-63, 69-69, 74-74, 85-85, 98-100, 107-109, 115-117, 124-126, 136-136, 141-141, 148-148, 155-155, 163-163, 167-167, 171-171, 175-175, 179-179, 183-183, 187-187, 191-191, 195-195, 199-199 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift` lines 32-46 — location member; effect enclosing struct XMLEncodingTests
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLEntitiesTests.swift` lines 15-15 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLEntitiesTests.swift` lines 28-36, 42-50, 56-58, 64-65, 72-79, 85-85, 91-91, 97-97, 105-113, 119-119, 125-125, 131-131, 139-141, 147-147, 156-168, 173-174, 185-198, 204-204, 211-212, 219-220, 226-226, 234-234, 240-240, 247-249, 255-255, 262-262, 269-269, 280-280, 291-291, 296-296, 303-303, 307-307 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLNamespaceContextTests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLNamespaceContextTests.swift` lines 20-20, 25-25, 30-30, 38-38, 47-47, 53-53, 60-60, 66-66, 71-71, 79-79, 89-89, 97-97, 105-105, 116-116, 126-126, 138-138, 153-153 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLSAXParserTests.swift` lines 11-11 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSParser/Tests/RSParserTests/XML/XMLSAXParserTests.swift` lines 15-15, 24-24, 34-34, 48-48, 59-59, 72-72, 84-84, 93-93, 108-108, 119-119, 124-124, 129-129, 134-134, 139-139, 145-145, 150-150, 159-159, 165-165, 171-171, 179-179, 184-184, 193-193, 207-207, 216-216, 225-225, 234-234, 246-246, 254-254, 260-260, 271-271, 282-282, 292-292, 303-303, 322-322, 340-340, 353-353, 367-367, 382-382, 398-398, 414-414 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift` lines 517-517 — location body; effect enclosing var lastOpenRSSOrgFeedRefresh
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/DownloadSession429Tests.swift` lines 17-17, 32-32 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/HTTPLinkPagingInfoTests.swift` lines 14-14, 21-21, 28-28, 35-35 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/MacWebBrowserTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/MacWebBrowserTests.swift` lines 17-17, 22-22, 27-27, 32-32, 42-42, 47-47, 53-53, 58-58, 64-64 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/SpecialCasesTests.swift` lines 14-14, 21-21, 27-27, 34-34 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolIsolationTests.swift` lines 18-18, 29-29, 50-50 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolMethodMatchingTests.swift` lines 18-18, 32-32, 49-49 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolRequestCountTests.swift` lines 18-18, 34-34, 49-49, 60-60 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/RSWeb/Tests/RSWebTests/URLPreparedForOpeningTests.swift` lines 14-14, 20-20, 29-29, 34-34 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/SyncDatabase/Tests/SyncDatabaseTests/SyncStatusTableTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Modules/SyncDatabase/Tests/SyncDatabaseTests/SyncStatusTableTests.swift` lines 18-18, 37-37, 46-46, 65-65, 87-87 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `Shared/AccountType+Helpers.swift` lines 22-22 — location member; effect enclosing extension AccountType
- `parse-error` `Shared/Assets.swift` lines 165-165 — location member; effect enclosing struct Colors
- `parse-error` `Shared/HelpURL.swift` lines 22-22 — location member; effect enclosing enum HelpURL
- `parse-error` `Shared/HelpURL.swift` lines 26-26 — location member; effect enclosing enum HelpURL
- `conditional-declaration` `Shared/SmartFeeds/PseudoFeed.swift` lines 9-31 — PseudoFeed is declared in 2 `#if` branches; every branch renders and none is evaluated
- `macro-not-expanded` `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift` lines 14-20, 28-28, 36-36, 44-44 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift` lines 12-12 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift` lines 14-14 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift` lines 17-17, 25-25, 33-33, 41-41, 48-48, 53-53, 57-57, 61-61, 66-66, 70-70 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift` lines 15-15 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift` lines 19-19, 25-26, 32-32, 38-38, 44-44, 50-50, 74-74, 88-89, 102-102, 109-109, 116-117, 127-127, 133-133, 139-140, 155-155, 164-165, 180-180, 190-191, 199-199, 204-204 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift` lines 16-16 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift` lines 22-22, 33-33, 38-38, 43-43, 48-48, 53-53, 58-58, 65-65 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/SanitizedTitleTests.swift` lines 15-15 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/SanitizedTitleTests.swift` lines 19-21, 25-27, 31-33, 43-43, 47-47, 51-51, 60-60, 64-64, 68-68, 75-75, 84-85, 94-94, 107-108, 115-116, 127-127, 131-131, 141-146, 150-155, 165-166, 170-171, 179-179, 192-193, 199-201, 206-206, 210-210 — attached macro @Test is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ThemeUnzipTests.swift` lines 13-13 — attached macro @Suite is not expanded; code it generates does not render
- `macro-not-expanded` `Tests/NetNewsWireTests/ThemeUnzipTests.swift` lines 15-15, 30-30 — attached macro @Test is not expanded; code it generates does not render
- `parse-error` `iOS/Article/WebViewController.swift` lines 580-580 — location body; effect enclosing func scrollPositionDidChange
- `parse-error` `iOS/KeyboardManager.swift` lines 110-110 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 114-114 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 118-118 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 122-122 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/SceneCoordinator.swift` lines 1530-1530 — location body; effect enclosing func showFeedInspector
- `macro-not-expanded` `iOS/Settings/AboutCreditView.swift` lines 44-46 — freestanding macro #Preview is not expanded; code it generates does not render
- `macro-not-expanded` `iOS/Settings/AboutView.swift` lines 71-73 — freestanding macro #Preview is not expanded; code it generates does not render
