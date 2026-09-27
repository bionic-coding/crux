# Module graph

_18 containers, 41 targets, 131 in-tree dependency edges and every Swift import, read from the literal manifest subset and the pinned Swift grammar; no manifest was evaluated and no dependency resolved._

## Containers

| container | container kind |
|---|---|
| `Modules/Account/Package.swift` | swift package |
| `Modules/ActivityLog/Package.swift` | swift package |
| `Modules/Articles/Package.swift` | swift package |
| `Modules/ArticlesDatabase/Package.swift` | swift package |
| `Modules/CloudKitSync/Package.swift` | swift package |
| `Modules/ErrorLog/Package.swift` | swift package |
| `Modules/FeedFinder/Package.swift` | swift package |
| `Modules/HTMLMetadata/Package.swift` | swift package |
| `Modules/Images/Package.swift` | swift package |
| `Modules/NewsBlur/Package.swift` | swift package |
| `Modules/RSCore/Package.swift` | swift package |
| `Modules/RSDatabase/Package.swift` | swift package |
| `Modules/RSParser/Package.swift` | swift package |
| `Modules/RSTree/Package.swift` | swift package |
| `Modules/RSWeb/Package.swift` | swift package |
| `Modules/Secrets/Package.swift` | swift package |
| `Modules/SyncDatabase/Package.swift` | swift package |
| `NetNewsWire.xcodeproj` | xcode project |

## Targets

| target | container | target kind | product type | conditional | declared at |
|---|---|---|---|---|---|
| `Account` | `Modules/Account/Package.swift` | library | — | — | `Modules/Account/Package.swift:29-30` |
| `AccountTests` | `Modules/Account/Package.swift` | test | — | — | `Modules/Account/Package.swift:51-52` |
| `ActivityLog` | `Modules/ActivityLog/Package.swift` | library | — | — | `Modules/ActivityLog/Package.swift:15-16` |
| `ActivityLogTests` | `Modules/ActivityLog/Package.swift` | test | — | — | `Modules/ActivityLog/Package.swift:24-25` |
| `Articles` | `Modules/Articles/Package.swift` | library | — | — | `Modules/Articles/Package.swift:17-18` |
| `ArticlesTests` | `Modules/Articles/Package.swift` | test | — | — | `Modules/Articles/Package.swift:26-27` |
| `ArticlesDatabase` | `Modules/ArticlesDatabase/Package.swift` | library | — | — | `Modules/ArticlesDatabase/Package.swift:20-21` |
| `ArticlesDatabaseTests` | `Modules/ArticlesDatabase/Package.swift` | test | — | — | `Modules/ArticlesDatabase/Package.swift:33-34` |
| `CloudKitSync` | `Modules/CloudKitSync/Package.swift` | library | — | — | `Modules/CloudKitSync/Package.swift:17-18` |
| `CloudKitSyncTests` | `Modules/CloudKitSync/Package.swift` | test | — | — | `Modules/CloudKitSync/Package.swift:27-28` |
| `ErrorLog` | `Modules/ErrorLog/Package.swift` | library | — | — | `Modules/ErrorLog/Package.swift:18-19` |
| `ErrorLogTests` | `Modules/ErrorLog/Package.swift` | test | — | — | `Modules/ErrorLog/Package.swift:30-31` |
| `FeedFinder` | `Modules/FeedFinder/Package.swift` | library | — | — | `Modules/FeedFinder/Package.swift:20-21` |
| `FeedFinderTests` | `Modules/FeedFinder/Package.swift` | test | — | — | `Modules/FeedFinder/Package.swift:34-35` |
| `HTMLMetadata` | `Modules/HTMLMetadata/Package.swift` | library | — | — | `Modules/HTMLMetadata/Package.swift:21-22` |
| `Images` | `Modules/Images/Package.swift` | library | — | — | `Modules/Images/Package.swift:23-24` |
| `NewsBlur` | `Modules/NewsBlur/Package.swift` | library | — | — | `Modules/NewsBlur/Package.swift:20-21` |
| `NewsBlurTests` | `Modules/NewsBlur/Package.swift` | test | — | — | `Modules/NewsBlur/Package.swift:29-30` |
| `RSCore` | `Modules/RSCore/Package.swift` | library | — | — | `Modules/RSCore/Package.swift:13-14` |
| `RSCoreObjC` | `Modules/RSCore/Package.swift` | library | — | — | `Modules/RSCore/Package.swift:21-22` |
| `RSCoreResources` | `Modules/RSCore/Package.swift` | library | — | — | `Modules/RSCore/Package.swift:28-29` |
| `RSCoreTests` | `Modules/RSCore/Package.swift` | test | — | — | `Modules/RSCore/Package.swift:39-40` |
| `RSDatabase` | `Modules/RSDatabase/Package.swift` | library | — | — | `Modules/RSDatabase/Package.swift:20-21` |
| `RSDatabaseObjC` | `Modules/RSDatabase/Package.swift` | library | — | — | `Modules/RSDatabase/Package.swift:28-29` |
| `RSDatabaseTests` | `Modules/RSDatabase/Package.swift` | test | — | — | `Modules/RSDatabase/Package.swift:32-33` |
| `RSParser` | `Modules/RSParser/Package.swift` | library | — | — | `Modules/RSParser/Package.swift:18-19` |
| `RSParserTests` | `Modules/RSParser/Package.swift` | test | — | — | `Modules/RSParser/Package.swift:26-27` |
| `RSTree` | `Modules/RSTree/Package.swift` | library | — | — | `Modules/RSTree/Package.swift:14-15` |
| `RSWeb` | `Modules/RSWeb/Package.swift` | library | — | — | `Modules/RSWeb/Package.swift:18-19` |
| `RSWebTests` | `Modules/RSWeb/Package.swift` | test | — | — | `Modules/RSWeb/Package.swift:30-31` |
| `Secrets` | `Modules/Secrets/Package.swift` | library | — | — | `Modules/Secrets/Package.swift:19-20` |
| `SyncDatabase` | `Modules/SyncDatabase/Package.swift` | library | — | — | `Modules/SyncDatabase/Package.swift:19-20` |
| `SyncDatabaseTests` | `Modules/SyncDatabase/Package.swift` | test | — | — | `Modules/SyncDatabase/Package.swift:32-33` |
| `NetNewsWire iOS Widget Extension` | `NetNewsWire.xcodeproj` | extension | app-extension | — | `NetNewsWire.xcodeproj/project.pbxproj:635-659` |
| `NetNewsWire Share Extension` | `NetNewsWire.xcodeproj` | extension | app-extension | — | `NetNewsWire.xcodeproj/project.pbxproj:660-681` |
| `NetNewsWire iOS Share Extension` | `NetNewsWire.xcodeproj` | extension | app-extension | — | `NetNewsWire.xcodeproj/project.pbxproj:682-706` |
| `NetNewsWire-iOSTests` | `NetNewsWire.xcodeproj` | test | unit-test | — | `NetNewsWire.xcodeproj/project.pbxproj:707-724` |
| `Subscribe to Feed` | `NetNewsWire.xcodeproj` | extension | app-extension | — | `NetNewsWire.xcodeproj/project.pbxproj:725-741` |
| `NetNewsWire-iOS` | `NetNewsWire.xcodeproj` | app | application | — | `NetNewsWire.xcodeproj/project.pbxproj:742-784` |
| `NetNewsWire` | `NetNewsWire.xcodeproj` | app | application | — | `NetNewsWire.xcodeproj/project.pbxproj:785-832` |
| `NetNewsWireTests` | `NetNewsWire.xcodeproj` | test | unit-test | — | `NetNewsWire.xcodeproj/project.pbxproj:833-860` |

## Graph

```mermaid
graph LR
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_CloudKitSync_Package_swift__CloudKitSync["CloudKitSync (Modules/CloudKitSync/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"]
  Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"] --> Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"]
  Modules_Account_Package_swift__AccountTests["AccountTests (Modules/Account/Package.swift)"] --> Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"]
  Modules_ActivityLog_Package_swift__ActivityLogTests["ActivityLogTests (Modules/ActivityLog/Package.swift)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_Articles_Package_swift__ArticlesTests["ArticlesTests (Modules/Articles/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabaseTests["ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabaseTests["ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)"] --> Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"]
  Modules_ArticlesDatabase_Package_swift__ArticlesDatabaseTests["ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_CloudKitSync_Package_swift__CloudKitSync["CloudKitSync (Modules/CloudKitSync/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_CloudKitSync_Package_swift__CloudKitSyncTests["CloudKitSyncTests (Modules/CloudKitSync/Package.swift)"] --> Modules_CloudKitSync_Package_swift__CloudKitSync["CloudKitSync (Modules/CloudKitSync/Package.swift)"]
  Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_ErrorLog_Package_swift__ErrorLogTests["ErrorLogTests (Modules/ErrorLog/Package.swift)"] --> Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"]
  Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_FeedFinder_Package_swift__FeedFinderTests["FeedFinderTests (Modules/FeedFinder/Package.swift)"] --> Modules_FeedFinder_Package_swift__FeedFinder["FeedFinder (Modules/FeedFinder/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"] --> Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"]
  Modules_NewsBlur_Package_swift__NewsBlurTests["NewsBlurTests (Modules/NewsBlur/Package.swift)"] --> Modules_NewsBlur_Package_swift__NewsBlur["NewsBlur (Modules/NewsBlur/Package.swift)"]
  Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"] --> Modules_RSCore_Package_swift__RSCoreObjC["RSCoreObjC (Modules/RSCore/Package.swift)"]
  Modules_RSCore_Package_swift__RSCoreTests["RSCoreTests (Modules/RSCore/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_RSDatabase_Package_swift__RSDatabaseTests["RSDatabaseTests (Modules/RSDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_RSDatabase_Package_swift__RSDatabaseTests["RSDatabaseTests (Modules/RSDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_RSParser_Package_swift__RSParserTests["RSParserTests (Modules/RSParser/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  Modules_RSWeb_Package_swift__RSWebTests["RSWebTests (Modules/RSWeb/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_RSWeb_Package_swift__RSWebTests["RSWebTests (Modules/RSWeb/Package.swift)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"] --> Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"]
  Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"] --> Modules_RSDatabase_Package_swift__RSDatabaseObjC["RSDatabaseObjC (Modules/RSDatabase/Package.swift)"]
  Modules_SyncDatabase_Package_swift__SyncDatabaseTests["SyncDatabaseTests (Modules/SyncDatabase/Package.swift)"] --> Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_CloudKitSync_Package_swift__CloudKitSync["CloudKitSync (Modules/CloudKitSync/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCoreObjC["RSCoreObjC (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCoreResources["RSCoreResources (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSTree_Package_swift__RSTree["RSTree (Modules/RSTree/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire_Share_Extension["NetNewsWire Share Extension (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__Subscribe_to_Feed["Subscribe to Feed (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWire_Share_Extension["NetNewsWire Share Extension (NetNewsWire.xcodeproj)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_Share_Extension["NetNewsWire Share Extension (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_Share_Extension["NetNewsWire Share Extension (NetNewsWire.xcodeproj)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"] --> Modules_RSTree_Package_swift__RSTree["RSTree (Modules/RSTree/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS_Widget_Extension["NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_Account_Package_swift__Account["Account (Modules/Account/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_ActivityLog_Package_swift__ActivityLog["ActivityLog (Modules/ActivityLog/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_ArticlesDatabase_Package_swift__ArticlesDatabase["ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_ErrorLog_Package_swift__ErrorLog["ErrorLog (Modules/ErrorLog/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_HTMLMetadata_Package_swift__HTMLMetadata["HTMLMetadata (Modules/HTMLMetadata/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_Images_Package_swift__Images["Images (Modules/Images/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_RSDatabase_Package_swift__RSDatabase["RSDatabase (Modules/RSDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_RSTree_Package_swift__RSTree["RSTree (Modules/RSTree/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_RSWeb_Package_swift__RSWeb["RSWeb (Modules/RSWeb/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_Secrets_Package_swift__Secrets["Secrets (Modules/Secrets/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> Modules_SyncDatabase_Package_swift__SyncDatabase["SyncDatabase (Modules/SyncDatabase/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire_iOS_Share_Extension["NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire_iOS_Widget_Extension["NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOSTests["NetNewsWire-iOSTests (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWire_iOSTests["NetNewsWire-iOSTests (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire_iOS["NetNewsWire-iOS (NetNewsWire.xcodeproj)"]
  NetNewsWire_xcodeproj__NetNewsWireTests["NetNewsWireTests (NetNewsWire.xcodeproj)"] --> Modules_Articles_Package_swift__Articles["Articles (Modules/Articles/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWireTests["NetNewsWireTests (NetNewsWire.xcodeproj)"] --> Modules_RSCore_Package_swift__RSCore["RSCore (Modules/RSCore/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWireTests["NetNewsWireTests (NetNewsWire.xcodeproj)"] --> Modules_RSParser_Package_swift__RSParser["RSParser (Modules/RSParser/Package.swift)"]
  NetNewsWire_xcodeproj__NetNewsWireTests["NetNewsWireTests (NetNewsWire.xcodeproj)"] --> NetNewsWire_xcodeproj__NetNewsWire["NetNewsWire (NetNewsWire.xcodeproj)"]
```

## Dependencies

| from | dependency | dependency kind | location | requirement | declared at |
|---|---|---|---|---|---|
| `Modules/Account` | `../ActivityLog` | path dependency | `Modules/ActivityLog` | — | `Modules/Account/Package.swift:14-14` |
| `Modules/Account` | `../Articles` | path dependency | `Modules/Articles` | — | `Modules/Account/Package.swift:15-15` |
| `Modules/Account` | `../ArticlesDatabase` | path dependency | `Modules/ArticlesDatabase` | — | `Modules/Account/Package.swift:16-16` |
| `Modules/Account` | `../CloudKitSync` | path dependency | `Modules/CloudKitSync` | — | `Modules/Account/Package.swift:17-17` |
| `Modules/Account` | `../FeedFinder` | path dependency | `Modules/FeedFinder` | — | `Modules/Account/Package.swift:18-18` |
| `Modules/Account` | `../Secrets` | path dependency | `Modules/Secrets` | — | `Modules/Account/Package.swift:19-19` |
| `Modules/Account` | `../ErrorLog` | path dependency | `Modules/ErrorLog` | — | `Modules/Account/Package.swift:20-20` |
| `Modules/Account` | `../SyncDatabase` | path dependency | `Modules/SyncDatabase` | — | `Modules/Account/Package.swift:21-21` |
| `Modules/Account` | `../RSWeb` | path dependency | `Modules/RSWeb` | — | `Modules/Account/Package.swift:22-22` |
| `Modules/Account` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/Account/Package.swift:23-23` |
| `Modules/Account` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/Account/Package.swift:24-24` |
| `Modules/Account` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/Account/Package.swift:25-25` |
| `Modules/Account` | `../NewsBlur` | path dependency | `Modules/NewsBlur` | — | `Modules/Account/Package.swift:26-26` |
| `Modules/Articles` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/Articles/Package.swift:14-14` |
| `Modules/ArticlesDatabase` | `../Articles` | path dependency | `Modules/Articles` | — | `Modules/ArticlesDatabase/Package.swift:14-14` |
| `Modules/ArticlesDatabase` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/ArticlesDatabase/Package.swift:15-15` |
| `Modules/ArticlesDatabase` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/ArticlesDatabase/Package.swift:16-16` |
| `Modules/ArticlesDatabase` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/ArticlesDatabase/Package.swift:17-17` |
| `Modules/CloudKitSync` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/CloudKitSync/Package.swift:14-14` |
| `Modules/ErrorLog` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/ErrorLog/Package.swift:14-14` |
| `Modules/ErrorLog` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/ErrorLog/Package.swift:15-15` |
| `Modules/FeedFinder` | `../RSWeb` | path dependency | `Modules/RSWeb` | — | `Modules/FeedFinder/Package.swift:14-14` |
| `Modules/FeedFinder` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/FeedFinder/Package.swift:15-15` |
| `Modules/FeedFinder` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/FeedFinder/Package.swift:16-16` |
| `Modules/FeedFinder` | `../ActivityLog` | path dependency | `Modules/ActivityLog` | — | `Modules/FeedFinder/Package.swift:17-17` |
| `Modules/HTMLMetadata` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/HTMLMetadata/Package.swift:14-14` |
| `Modules/HTMLMetadata` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/HTMLMetadata/Package.swift:15-15` |
| `Modules/HTMLMetadata` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/HTMLMetadata/Package.swift:16-16` |
| `Modules/HTMLMetadata` | `../RSWeb` | path dependency | `Modules/RSWeb` | — | `Modules/HTMLMetadata/Package.swift:17-17` |
| `Modules/HTMLMetadata` | `../ActivityLog` | path dependency | `Modules/ActivityLog` | — | `Modules/HTMLMetadata/Package.swift:18-18` |
| `Modules/Images` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/Images/Package.swift:14-14` |
| `Modules/Images` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/Images/Package.swift:15-15` |
| `Modules/Images` | `../RSWeb` | path dependency | `Modules/RSWeb` | — | `Modules/Images/Package.swift:16-16` |
| `Modules/Images` | `../Account` | path dependency | `Modules/Account` | — | `Modules/Images/Package.swift:17-17` |
| `Modules/Images` | `../Articles` | path dependency | `Modules/Articles` | — | `Modules/Images/Package.swift:18-18` |
| `Modules/Images` | `../HTMLMetadata` | path dependency | `Modules/HTMLMetadata` | — | `Modules/Images/Package.swift:19-19` |
| `Modules/Images` | `../ActivityLog` | path dependency | `Modules/ActivityLog` | — | `Modules/Images/Package.swift:20-20` |
| `Modules/NewsBlur` | `../Secrets` | path dependency | `Modules/Secrets` | — | `Modules/NewsBlur/Package.swift:14-14` |
| `Modules/NewsBlur` | `../RSWeb` | path dependency | `Modules/RSWeb` | — | `Modules/NewsBlur/Package.swift:15-15` |
| `Modules/NewsBlur` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/NewsBlur/Package.swift:16-16` |
| `Modules/NewsBlur` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/NewsBlur/Package.swift:17-17` |
| `Modules/RSParser` | `https://github.com/brentsimmons/Tidemark` | remote package | `https://github.com/brentsimmons/Tidemark` | from: 1.0.0 | `Modules/RSParser/Package.swift:14-14` |
| `Modules/RSParser` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/RSParser/Package.swift:15-15` |
| `Modules/RSWeb` | `../RSParser` | path dependency | `Modules/RSParser` | — | `Modules/RSWeb/Package.swift:14-14` |
| `Modules/RSWeb` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/RSWeb/Package.swift:15-15` |
| `Modules/Secrets` | `../ErrorLog` | path dependency | `Modules/ErrorLog` | — | `Modules/Secrets/Package.swift:15-15` |
| `Modules/Secrets` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/Secrets/Package.swift:16-16` |
| `Modules/SyncDatabase` | `../Articles` | path dependency | `Modules/Articles` | — | `Modules/SyncDatabase/Package.swift:14-14` |
| `Modules/SyncDatabase` | `../RSCore` | path dependency | `Modules/RSCore` | — | `Modules/SyncDatabase/Package.swift:15-15` |
| `Modules/SyncDatabase` | `../RSDatabase` | path dependency | `Modules/RSDatabase` | — | `Modules/SyncDatabase/Package.swift:16-16` |
| `NetNewsWire-iOS` | `Zip` | remote product | `https://github.com/marmelroy/Zip.git` | revision bca30f6d6c7d37cbc4aa8f6b0002e281dcc36195 | `NetNewsWire.xcodeproj/project.pbxproj:771-771` |
| `NetNewsWire` | `Sparkle` | remote product | `https://github.com/sparkle-project/Sparkle.git` | upToNextMajorVersion 2.9.5 | `NetNewsWire.xcodeproj/project.pbxproj:813-813` |
| `NetNewsWire` | `CrashReporter` | remote product | `https://github.com/microsoft/plcrashreporter.git` | upToNextMajorVersion 1.8.1 | `NetNewsWire.xcodeproj/project.pbxproj:814-814` |
| `NetNewsWire` | `Zip` | remote product | `https://github.com/marmelroy/Zip.git` | revision bca30f6d6c7d37cbc4aa8f6b0002e281dcc36195 | `NetNewsWire.xcodeproj/project.pbxproj:818-818` |
| `project` | `https://github.com/sparkle-project/Sparkle.git` | remote package | `https://github.com/sparkle-project/Sparkle.git` | upToNextMajorVersion 2.9.5 | `NetNewsWire.xcodeproj/project.pbxproj:1467-1474` |
| `project` | `https://github.com/marmelroy/Zip.git` | remote package | `https://github.com/marmelroy/Zip.git` | revision bca30f6d6c7d37cbc4aa8f6b0002e281dcc36195 | `NetNewsWire.xcodeproj/project.pbxproj:1475-1482` |
| `project` | `https://github.com/microsoft/plcrashreporter.git` | remote package | `https://github.com/microsoft/plcrashreporter.git` | upToNextMajorVersion 1.8.1 | `NetNewsWire.xcodeproj/project.pbxproj:1483-1490` |

## Imports

| file | module | import kind | owning target | resolves to |
|---|---|---|---|---|
| `Mac/About/AboutWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/About/LinkLabel.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/About/LinkLabel.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/About/LinksTextView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/About/LinksTextView.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/AccountStats/AccountStatsWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AccountStats/AccountStatsWindowController.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/AccountStats/AccountStatsWindowController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/AccountStats/AccountStatsWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/ActivityLog/ActivityLogWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ActivityLog/ActivityLogWindowController.swift:9-9` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/ActivityLog/ActivityLogWindowController.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/ActivityLog/ActivityLogWindowController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/ActivityLog/ActivityLogWindowController.swift:12-12` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Mac/AppDefaults.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:10-10` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/AppDelegate.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/AppDelegate.swift:14-14` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Mac/AppDelegate.swift:15-15` | `ErrorLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Mac/AppDelegate.swift:16-16` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/AppDelegate.swift:17-17` | `RSCoreObjC` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCoreObjC (Modules/RSCore/Package.swift)` |
| `Mac/AppDelegate.swift:18-18` | `RSCoreResources` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCoreResources (Modules/RSCore/Package.swift)` |
| `Mac/AppDelegate.swift:19-19` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/AppDelegate.swift:20-20` | `Secrets` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Mac/AppDelegate.swift:21-21` | `CrashReporter` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:22-22` | `Sparkle` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/AppDelegate.swift:23-23` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/AppDelegate.swift:24-24` | `HTMLMetadata` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `Mac/Browser.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Browser.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpContentView.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpStatusView.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpViewController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpViewController.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/CloudKitStats/CloudKitStatsLayout.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CloudKitStatsToolbarView.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CloudKitStatsViewController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/CloudKitStatsViewController.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/CloudKitStats/CloudKitStatsViewController.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/CloudKitStats/CloudKitStatsWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanContentView.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanStatusView.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanViewController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanViewController.swift:9-9` | `CloudKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanViewController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanViewController.swift:11-11` | `CloudKitSync` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Mac/CrashReporter/CrashReportWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CrashReporter/CrashReporter.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CrashReporter/CrashReporter.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/CrashReporter/CrashReporter.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/CrashReporter/CrashReporter.swift:12-12` | `CrashReporter` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CurrentActivity/CurrentActivityWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/CurrentActivity/CurrentActivityWindowController.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/CurrentActivity/CurrentActivityWindowController.swift:10-10` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Mac/CurrentActivity/CurrentActivityWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/Dinosaurs/DinosaursWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Dinosaurs/DinosaursWindowController.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Dinosaurs/DinosaursWindowController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Dinosaurs/DinosaursWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/ErrorHandler.swift:9-9` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/ErrorHandler.swift:10-10` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ErrorHandler.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/ErrorHandler.swift:12-12` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ErrorLog/ErrorLogWindowController.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ErrorLog/ErrorLogWindowController.swift:9-9` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/ErrorLog/ErrorLogWindowController.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/ErrorLog/ErrorLogWindowController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/ErrorLog/ErrorLogWindowController.swift:12-12` | `ErrorLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Mac/Inspector/BuiltinSmartFeedInspectorViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/FeedInspectorViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/FeedInspectorViewController.swift:10-10` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/FeedInspectorViewController.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/FeedInspectorViewController.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Inspector/FeedInspectorViewController.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Inspector/FeedInspectorViewController.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/Inspector/FolderInspectorViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/FolderInspectorViewController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Inspector/FolderInspectorViewController.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Inspector/InspectorWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Inspector/NothingInspectorViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/LogTextStyle.swift:8-8` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:11-11` | `RSCoreResources` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCoreResources (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:12-12` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:13-13` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:14-14` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift:15-15` | `RSParser` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:11-11` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/AddFeed/FolderTreeMenu.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/AddFeed/FolderTreeMenu.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/AddFeed/FolderTreeMenu.swift:11-11` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/AddFeed/FolderTreeMenu.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/AddFolder/AddFolderWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/AddFolder/AddFolderWindowController.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/AddFolder/AddFolderWindowController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/ArticleExtractorButton.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/ColumnLayoutSplitView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailContainerView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailIconSchemeHandler.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailIconSchemeHandler.swift:10-10` | `WebKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailIconSchemeHandler.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Detail/DetailStatusBarView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailStatusBarView.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Detail/DetailViewController.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailViewController.swift:10-10` | `WebKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailViewController.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Detail/DetailViewController.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Detail/DetailViewController.swift:13-13` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/MainWindow/Detail/DetailWebView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailWebView.swift:10-10` | `WebKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailWebView.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:10-10` | `WebKit` | @preconcurrency | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:13-13` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Detail/DetailWebViewController.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Detail/DetailWindowState.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/Keyboard/DetailKeyboardDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Detail/Keyboard/DetailKeyboardDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/IconView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/IconView.swift:10-10` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Keyboard/MainWindowKeyboardHandler.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Keyboard/MainWindowKeyboardHandler.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/MainWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/MainWindowController.swift:10-10` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/MainWindowController.swift:11-11` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/MainWindowController.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/MainWindowController.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/MainWindowController.swift:14-14` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/MainWindowState.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/NNW3/NNW3Document.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/NNW3/NNW3Document.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/NNW3/NNW3ImportController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/NNW3/NNW3ImportController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/NNW3/NNW3OpenPanelAccessoryViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/NNW3/NNW3OpenPanelAccessoryViewController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/OPML/ExportOPMLWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/OPML/ExportOPMLWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/OPML/ExportOPMLWindowController.swift:11-11` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Mac/MainWindow/OPML/ExportOPMLWindowController.swift:12-12` | `UniformTypeIdentifiers` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/OPML/ImportOPMLWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/OPML/ImportOPMLWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/OPML/ImportOPMLWindowController.swift:11-11` | `UniformTypeIdentifiers` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/SharingServiceDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/SharingServicePickerDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/SharingServicePickerDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift:12-12` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift:13-13` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCellAppearance.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/Cell/SidebarCellLayout.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/Cell/SidebarCellLayout.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/Keyboard/SidebarKeyboardDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/Keyboard/SidebarKeyboardDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/PasteboardFeed.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/PasteboardFeed.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Sidebar/PasteboardFeed.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/PasteboardFeed.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/PasteboardFolder.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/PasteboardFolder.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/PasteboardFolder.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/Renaming/RenameWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarDeleteItemsAlert.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarDeleteItemsAlert.swift:10-10` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarDeleteItemsAlert.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift:10-10` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarOutlineView.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarOutlineView.swift:11-11` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift:12-12` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift:13-13` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:10-10` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:13-13` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Sidebar/SidebarWindowState.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Sidebar/UnreadCountView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/ArticlePasteboardWriter.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/ArticlePasteboardWriter.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/ArticlePasteboardWriter.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellAppearance.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Cell/TimelineCellData.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Cell/TimelineCellData.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellData.swift:11-11` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellLayout.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Cell/TimelineCellLayout.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/Cell/TimelineColumnCellViews.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Cell/TimelineTableCellView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Cell/TimelineTableCellView.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/Cell/UnreadIndicatorView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Keyboard/TimelineKeyboardDelegate.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/Keyboard/TimelineKeyboardDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineColumn.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineContainerView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineContainerViewController.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineLayout.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineTableRowView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineTableView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineTableView.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController+ColumnLayout.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineViewController+ColumnLayout.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController+ContextualMenus.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineViewController+ContextualMenus.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController+ContextualMenus.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController+ContextualMenus.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:13-13` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/MainWindow/Timeline/TimelineViewController.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Mac/MainWindow/Timeline/TimelineWindowState.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountCell.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsAddCloudKitWindowController.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsAddCloudKitWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsAddLocalWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsAddLocalWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsDetailView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsDetailView.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsDetailViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsDetailViewController.swift:10-10` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsDetailViewController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsFeedbinWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsFeedbinWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsFeedbinWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsFeedbinWindowController.swift:12-12` | `Secrets` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsNewsBlurWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsNewsBlurWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsNewsBlurWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsNewsBlurWindowController.swift:12-12` | `Secrets` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:10-10` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsReaderAPIWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AccountsReaderAPIWindowController.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsReaderAPIWindowController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/Preferences/Accounts/AccountsReaderAPIWindowController.swift:12-12` | `Secrets` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Mac/Preferences/Accounts/AddAccountHelpView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AddAccountHelpView.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AddAccountsView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/Accounts/AddAccountsView.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Preferences/Accounts/AddAccountsView.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Preferences/Advanced/AdvancedPreferencesViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift:12-12` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift:13-13` | `UniformTypeIdentifiers` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/PreferencesControlsBackgroundView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/PreferencesControlsBackgroundView.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Preferences/PreferencesTableViewBackgroundView.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Preferences/PreferencesWindowController.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/SafariExtension/SafariExtensionHandler.swift:9-9` | `SafariServices` | @preconcurrency | `Subscribe to Feed (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Account+Scriptability.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Account+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/Account+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Account+Scriptability.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Scripting/AppDelegate+Scriptability.swift:19-19` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/AppDelegate+Scriptability.swift:20-20` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/AppDelegate+Scriptability.swift:21-21` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Article+Scriptability.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Article+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/Article+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Author+Scriptability.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Author+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/Author+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Feed+Scriptability.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Feed+Scriptability.swift:10-10` | `RSParser` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Mac/Scripting/Feed+Scriptability.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/Feed+Scriptability.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Folder+Scriptability.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/Folder+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/Folder+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/Folder+Scriptability.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Mac/Scripting/MainWindowController+Scriptability.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/MainWindowController+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/MainWindowController+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/NSApplication+Scriptability.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/NSApplication+Scriptability.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/NSApplication+Scriptability.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Mac/Scripting/NSScriptCommand+NetNewsWire.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/NSScriptCommand+NetNewsWire.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/Scripting/ScriptingObject.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/ScriptingObjectContainer.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/Scripting/ScriptingObjectContainer.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Mac/ShareExtension/ShareViewController.swift:9-9` | `AppKit` | plain | `NetNewsWire Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ShareExtension/ShareViewController.swift:10-10` | `UniformTypeIdentifiers` | plain | `NetNewsWire Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Mac/ShareExtension/ShareViewController.swift:11-11` | `os` | plain | `NetNewsWire Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Account.swift:10-10` | `UIKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Account.swift:13-13` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Account.swift:14-14` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:15-15` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:16-16` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:17-17` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:18-18` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:19-19` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:20-20` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:21-21` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:22-22` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/Account.swift:23-23` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountBehaviors.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountDelegate.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/AccountDelegate.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/AccountDelegate.swift:12-12` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/AccountDelegate.swift:13-13` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/AccountError.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountError.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountManager.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountManager.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:12-12` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:13-13` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:14-14` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:15-15` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/AccountManager.swift:16-16` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettings.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountSettings.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettings.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettingsDatabase.swift:10-10` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountSettingsDatabase.swift:11-11` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettingsDatabase.swift:12-12` | `RSDatabaseObjC` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettingsImporter.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountSettingsImporter.swift:9-9` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/AccountSettingsImporter.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/AccountSettingsImporter.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/ArticleFetcher.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ArticleFetcher.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/ArticleFetcher.swift:11-11` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CKRecord+Extensions.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CKRecord+Extensions.swift:10-10` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:10-10` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:11-11` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:12-12` | `SystemConfiguration` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:13-13` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:14-14` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:15-15` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:16-16` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:17-17` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:18-18` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:19-19` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:20-20` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:21-21` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:22-22` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift:23-23` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:12-12` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:13-13` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:14-14` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZone.swift:15-15` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:12-12` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:13-13` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:14-14` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitAccountZoneDelegate.swift:15-15` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticleStatusUpdate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticleStatusUpdate.swift:10-10` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticleStatusUpdate.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:11-11` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:12-12` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:13-13` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:14-14` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:15-15` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZone.swift:16-16` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:12-12` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:13-13` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:14-14` | `CloudKit` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:15-15` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:16-16` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:17-17` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitArticlesZoneDelegate.swift:18-18` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitReceiveStatusOperation.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitReceiveStatusOperation.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitReceiveStatusOperation.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitReceiveStatusOperation.swift:12-12` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitReceiveStatusOperation.swift:13-13` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitRemoteNotificationOperation.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitRemoteNotificationOperation.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitRemoteNotificationOperation.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitRemoteNotificationOperation.swift:12-12` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitRemoteNotificationOperation.swift:13-13` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:11-11` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:12-12` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:13-13` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:14-14` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:15-15` | `CloudKitSync` | plain | `Account (Modules/Account/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSendStatusOperation.swift:16-16` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitStats.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitStatsViewModel.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSyncMessage.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CloudKit/CloudKitSyncMessage.swift:9-9` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/CloudKit/CloudKitWebDocumentation.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/CombinedRefreshProgress.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Container.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Container.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Container.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/ContainerIdentifier.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ContainerPath.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/DataExtensions.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/DataExtensions.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/DataExtensions.swift:11-11` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feed.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feed.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feed.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feed.swift:12-12` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettings.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/FeedSettings.swift:9-9` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettings.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:9-9` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:11-11` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:12-12` | `RSDatabaseObjC` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:13-13` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsDatabase.swift:14-14` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsImporter.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/FeedSettingsImporter.swift:9-9` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/FeedSettingsImporter.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/FeedSettingsImporter.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/Feedbin.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/Feedbin.swift:9-9` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/Feedbin.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAPICaller.swift:13-13` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAPICaller.swift:14-14` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAPICaller.swift:15-15` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:10-10` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:12-12` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:13-13` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:14-14` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:15-15` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:16-16` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:17-17` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:18-18` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:19-19` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinAccountDelegate.swift:20-20` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinDate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinEntry.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinEntry.swift:10-10` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinEntry.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinImportResult.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinStarredEntry.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinSubscription.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinSubscription.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinSubscription.swift:11-11` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feedbin/FeedbinTag.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinTagging.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedbin/FeedbinUnreadEntry.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/Feedly.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/Feedly.swift:9-9` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/Feedly.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAPICaller.swift:12-12` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate+OAuth.swift:11-11` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:10-10` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:12-12` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:13-13` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:14-14` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:15-15` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:16-16` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:17-17` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:18-18` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegate.swift:19-19` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/FeedlyAccountDelegateError.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyFolderReconciliation.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyModel.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/FeedlyModel.swift:9-9` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:10-10` | `AuthenticationServices` | @preconcurrency | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:11-11` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:12-12` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/OAuthAccountAuthorizationOperation.swift:13-13` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationClient+Feedly.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationClient+Feedly.swift:10-10` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/Feedly/OAuthAuthorizationCodeGranting.swift:11-11` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/Folder.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/Folder.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/Folder.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/InitialFeedDownloader.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/LocalAccount/InitialFeedDownloader.swift:10-10` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/InitialFeedDownloader.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/InitialFeedDownloader.swift:12-12` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:11-11` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:12-12` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:13-13` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:14-14` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:15-15` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountDelegate.swift:16-16` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:10-10` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:12-12` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:13-13` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:14-14` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:15-15` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:16-16` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/LocalAccount/LocalAccountRefresher.swift:17-17` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:10-10` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:11-11` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:12-12` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:13-13` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:14-14` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:15-15` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:16-16` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:17-17` | `NewsBlur` | plain | `Account (Modules/Account/Package.swift)` | `NewsBlur (Modules/NewsBlur/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:18-18` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/Internals/NewsBlurAccountDelegate+Internal.swift:19-19` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:11-11` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:12-12` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:13-13` | `RSDatabase` | plain | `Account (Modules/Account/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:14-14` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:15-15` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:16-16` | `NewsBlur` | plain | `Account (Modules/Account/Package.swift)` | `NewsBlur (Modules/NewsBlur/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:17-17` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:18-18` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/NewsBlur/NewsBlurAccountDelegate.swift:19-19` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/OPMLFile.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/OPMLFile.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/OPMLFile.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/OPMLFile.swift:12-12` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/OPMLNormalizer.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/OPMLNormalizer.swift:10-10` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:10-10` | `ActivityLog` | plain | `Account (Modules/Account/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:11-11` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:12-12` | `ErrorLog` | plain | `Account (Modules/Account/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:13-13` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:14-14` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:15-15` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:16-16` | `FeedFinder` | plain | `Account (Modules/Account/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:17-17` | `SyncDatabase` | plain | `Account (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:18-18` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIAccountDelegate.swift:19-19` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:10-10` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:11-11` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPICaller.swift:12-12` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIEntry.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIEntry.swift:10-10` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIEntry.swift:11-11` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPISubscription.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPISubscription.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPISubscription.swift:11-11` | `RSParser` | plain | `Account (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPITag.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPITagging.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIUnreadEntry.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/ReaderAPIVariant.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/URLRequest+ReaderAPI.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/ReaderAPI/URLRequest+ReaderAPI.swift:9-9` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/ReaderAPI/URLRequest+ReaderAPI.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/SidebarItem.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/SidebarItem.swift:10-10` | `RSCore` | plain | `Account (Modules/Account/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Account/Sources/Account/SidebarItemIdentifier.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/SingleArticleFetcher.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/SingleArticleFetcher.swift:10-10` | `Articles` | plain | `Account (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Sources/Account/SingleArticleFetcher.swift:11-11` | `ArticlesDatabase` | plain | `Account (Modules/Account/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/Account/Sources/Account/SyncRateLimiter.swift:8-8` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/SyncRateLimiter.swift:9-9` | `os` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/SyncRateLimiter.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/URLRequest+Account.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Sources/Account/URLRequest+Account.swift:10-10` | `RSWeb` | plain | `Account (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Sources/Account/URLRequest+Account.swift:11-11` | `NewsBlur` | plain | `Account (Modules/Account/Package.swift)` | `NewsBlur (Modules/NewsBlur/Package.swift)` |
| `Modules/Account/Sources/Account/URLRequest+Account.swift:12-12` | `Secrets` | plain | `Account (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Sources/Account/UnreadCountProvider.swift:9-9` | `Foundation` | plain | `Account (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/AccountCredentialsTest.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/AccountCredentialsTest.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountCredentialsTest.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountCredentialsTest.swift:12-12` | `Secrets` | plain | `AccountTests (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountOPMLLoadTests.swift:8-8` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/AccountOPMLLoadTests.swift:9-9` | `RSParser` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountOPMLLoadTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountSettingsImporterTests.swift:8-8` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/AccountSettingsImporterTests.swift:9-9` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/AccountSettingsImporterTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/FeedSettingsDatabaseTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/FeedSettingsDatabaseTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/FeedSettingsDatabaseTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/FeedSettingsImporterTests.swift:8-8` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/FeedSettingsImporterTests.swift:9-9` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/FeedSettingsImporterTests.swift:10-10` | `Articles` | plain | `AccountTests (Modules/Account/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Account/Tests/AccountTests/FeedSettingsImporterTests.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderContentsSyncTest.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderContentsSyncTest.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderContentsSyncTest.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderSyncTest.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderSyncTest.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinFolderSyncTest.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinSyncTest.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinSyncTest.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/AccountFeedbinSyncTest.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinFeedNameTests.swift:8-8` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinFeedNameTests.swift:9-9` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinFeedNameTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift:8-8` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift:9-9` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift:10-10` | `SyncDatabase` | plain | `AccountTests (Modules/Account/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedbin/FeedbinStatusSendTests.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyActivityMessageTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyActivityMessageTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyActivityMessageTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyCollectionParserTests.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyCollectionParserTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyEntryParserTests.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyEntryParserTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFeedNameTests.swift:8-8` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFeedNameTests.swift:9-9` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFeedParserTests.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFeedParserTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFolderReconciliationTests.swift:8-8` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyFolderReconciliationTests.swift:9-9` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift:11-11` | `Secrets` | plain | `AccountTests (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyReauthorizationTests.swift:12-12` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyResourceIdTests.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyResourceIdTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyTextSanitizationTests.swift:9-9` | `XCTest` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyTextSanitizationTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyUnmarkableArticleIDsTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyUnmarkableArticleIDsTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/Feedly/FeedlyUnmarkableArticleIDsTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTrait.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTrait.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTrait.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTraitTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTraitTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/IsolatedWebserviceResponsesTraitTests.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/NewsBlur/NewsBlurFeedNameTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/NewsBlur/NewsBlurFeedNameTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/NewsBlur/NewsBlurFeedNameTests.swift:10-10` | `NewsBlur` | plain | `AccountTests (Modules/Account/Package.swift)` | `NewsBlur (Modules/NewsBlur/Package.swift)` |
| `Modules/Account/Tests/AccountTests/NewsBlur/NewsBlurFeedNameTests.swift:11-11` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/ReaderAPI/ReaderAPIEntryTests.swift:8-8` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/ReaderAPI/ReaderAPIEntryTests.swift:9-9` | `Testing` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/ReaderAPI/ReaderAPIEntryTests.swift:10-10` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/TestAccountManager.swift:9-9` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/TestAccountManager.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Account/Tests/AccountTests/TestAccountManager.swift:11-11` | `Secrets` | plain | `AccountTests (Modules/Account/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/Account/Tests/AccountTests/TestAccountManager.swift:13-13` | `Account` | @testable | `AccountTests (Modules/Account/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Account/Tests/AccountTests/TestingURLProtocol+Responses.swift:9-9` | `Foundation` | plain | `AccountTests (Modules/Account/Package.swift)` | sdk-or-unresolved |
| `Modules/Account/Tests/AccountTests/TestingURLProtocol+Responses.swift:10-10` | `RSWeb` | plain | `AccountTests (Modules/Account/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/ActivityLog/Sources/ActivityLog/Activity.swift:8-8` | `Foundation` | plain | `ActivityLog (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Sources/ActivityLog/ActivityKind.swift:8-8` | `Foundation` | plain | `ActivityLog (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Sources/ActivityLog/ActivityLog.swift:8-8` | `Foundation` | plain | `ActivityLog (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Sources/ActivityLog/ActivityLogDataSize.swift:8-8` | `Foundation` | plain | `ActivityLog (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Sources/ActivityLog/ActivityOwner.swift:8-8` | `Foundation` | plain | `ActivityLog (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Tests/ActivityLogTests/ActivityLogTests.swift:8-8` | `Testing` | plain | `ActivityLogTests (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Tests/ActivityLogTests/ActivityLogTests.swift:9-9` | `Foundation` | plain | `ActivityLogTests (Modules/ActivityLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ActivityLog/Tests/ActivityLogTests/ActivityLogTests.swift:10-10` | `ActivityLog` | @testable | `ActivityLogTests (Modules/ActivityLog/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Articles/Sources/Articles/Article.swift:9-9` | `Foundation` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/Article.swift:10-10` | `RSCore` | plain | `Articles (Modules/Articles/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Articles/Sources/Articles/ArticleStatus.swift:9-9` | `Foundation` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/ArticleStatus.swift:10-10` | `os` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/Author.swift:9-9` | `Foundation` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/Author.swift:10-10` | `RSCore` | plain | `Articles (Modules/Articles/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Articles/Sources/Articles/AuthorCache.swift:8-8` | `Foundation` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/AuthorCache.swift:9-9` | `os` | plain | `Articles (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Sources/Articles/AuthorCache.swift:10-10` | `RSCore` | plain | `Articles (Modules/Articles/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Articles/Tests/ArticlesTests/AuthorCacheTests.swift:8-8` | `Foundation` | plain | `ArticlesTests (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Tests/ArticlesTests/AuthorCacheTests.swift:9-9` | `Testing` | plain | `ArticlesTests (Modules/Articles/Package.swift)` | sdk-or-unresolved |
| `Modules/Articles/Tests/ArticlesTests/AuthorCacheTests.swift:11-11` | `Articles` | @testable | `ArticlesTests (Modules/Articles/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:10-10` | `os` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:11-11` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:12-12` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:13-13` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift:14-14` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:10-10` | `os` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:11-11` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:12-12` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:13-13` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:14-14` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift:15-15` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:8-8` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:9-9` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:10-10` | `os` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:11-11` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:12-12` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/AuthorsSchemaMigration.swift:13-13` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Constants.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Article+Database.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Article+Database.swift:10-10` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Article+Database.swift:11-11` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Article+Database.swift:12-12` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Article+Database.swift:13-13` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ArticleStatus+Database.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ArticleStatus+Database.swift:10-10` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ArticleStatus+Database.swift:11-11` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ArticleStatus+Database.swift:12-12` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Author+Database.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Author+Database.swift:10-10` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/Author+Database.swift:11-11` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ParsedArticle+Database.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ParsedArticle+Database.swift:10-10` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Extensions/ParsedArticle+Database.swift:11-11` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:10-10` | `os` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:11-11` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:12-12` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/Operations/FetchAllUnreadCountsOperation.swift:13-13` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:10-10` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:11-11` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:12-12` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:13-13` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/SearchTable.swift:14-14` | `RSParser` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:9-9` | `Foundation` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:10-10` | `os` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:11-11` | `RSCore` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:12-12` | `RSDatabase` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:13-13` | `RSDatabaseObjC` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift:14-14` | `Articles` | plain | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift:8-8` | `Foundation` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift:9-9` | `Testing` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift:10-10` | `Articles` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift:11-11` | `RSParser` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/ArticleUpdateTests.swift:12-12` | `ArticlesDatabase` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift:8-8` | `Foundation` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift:9-9` | `Testing` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift:10-10` | `Articles` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift:11-11` | `RSParser` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/StatusDivergenceTests.swift:12-12` | `ArticlesDatabase` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift:8-8` | `Foundation` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift:9-9` | `Testing` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift:10-10` | `Articles` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift:11-11` | `RSParser` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/ArticlesDatabase/Tests/ArticlesDatabaseTests/TodayQueriesTests.swift:12-12` | `ArticlesDatabase` | plain | `ArticlesDatabaseTests (Modules/ArticlesDatabase/Package.swift)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:9-9` | `Foundation` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitError.swift:10-10` | `CloudKit` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitLogger.swift:8-8` | `Foundation` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitLogger.swift:9-9` | `RSCore` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitLogger.swift:10-10` | `os` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:9-9` | `CloudKit` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:10-10` | `os` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZone.swift:11-11` | `RSCore` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZoneResult.swift:9-9` | `Foundation` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Sources/CloudKitSync/CloudKitZoneResult.swift:10-10` | `CloudKit` | plain | `CloudKitSync (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Tests/CloudKitSyncTests/CloudKitSyncTests.swift:1-1` | `XCTest` | plain | `CloudKitSyncTests (Modules/CloudKitSync/Package.swift)` | sdk-or-unresolved |
| `Modules/CloudKitSync/Tests/CloudKitSyncTests/CloudKitSyncTests.swift:2-2` | `CloudKitSync` | @testable | `CloudKitSyncTests (Modules/CloudKitSync/Package.swift)` | `CloudKitSync (Modules/CloudKitSync/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:8-8` | `Foundation` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:9-9` | `RSCore` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:10-10` | `RSDatabase` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift:11-11` | `RSDatabaseObjC` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:8-8` | `Foundation` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogEntry.swift:9-9` | `RSDatabase` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogNotification.swift:8-8` | `Foundation` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogTable.swift:8-8` | `Foundation` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogTable.swift:9-9` | `RSDatabase` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/ErrorLog/Sources/ErrorLog/ErrorLogTable.swift:10-10` | `RSDatabaseObjC` | plain | `ErrorLog (Modules/ErrorLog/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/ErrorLog/Tests/ErrorLogTests/ErrorLogDatabaseTests.swift:8-8` | `Testing` | plain | `ErrorLogTests (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Tests/ErrorLogTests/ErrorLogDatabaseTests.swift:9-9` | `Foundation` | plain | `ErrorLogTests (Modules/ErrorLog/Package.swift)` | sdk-or-unresolved |
| `Modules/ErrorLog/Tests/ErrorLogTests/ErrorLogDatabaseTests.swift:10-10` | `ErrorLog` | @testable | `ErrorLogTests (Modules/ErrorLog/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:9-9` | `Foundation` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | sdk-or-unresolved |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:10-10` | `os` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | sdk-or-unresolved |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:11-11` | `RSParser` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:12-12` | `RSWeb` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:13-13` | `RSCore` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/FeedFinder.swift:14-14` | `ActivityLog` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:9-9` | `Foundation` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | sdk-or-unresolved |
| `Modules/FeedFinder/Sources/FeedFinder/FeedSpecifier.swift:10-10` | `RSWeb` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/FeedFinder/Sources/FeedFinder/HTMLFeedFinder.swift:9-9` | `Foundation` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | sdk-or-unresolved |
| `Modules/FeedFinder/Sources/FeedFinder/HTMLFeedFinder.swift:10-10` | `RSParser` | plain | `FeedFinder (Modules/FeedFinder/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/FeedFinder/Tests/FeedFinderTests/FeedFinderTests.swift:9-9` | `XCTest` | plain | `FeedFinderTests (Modules/FeedFinder/Package.swift)` | sdk-or-unresolved |
| `Modules/FeedFinder/Tests/FeedFinderTests/FeedFinderTests.swift:10-10` | `FeedFinder` | @testable | `FeedFinderTests (Modules/FeedFinder/Package.swift)` | `FeedFinder (Modules/FeedFinder/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:8-8` | `Foundation` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:9-9` | `RSCore` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:10-10` | `RSDatabase` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDatabase.swift:11-11` | `RSDatabaseObjC` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:9-9` | `Foundation` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:10-10` | `os` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:11-11` | `RSCore` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:12-12` | `RSParser` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:13-13` | `RSWeb` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataDownloader.swift:14-14` | `ActivityLog` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataNotification.swift:8-8` | `Foundation` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:8-8` | `Foundation` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataRecord.swift:9-9` | `RSParser` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataTable.swift:8-8` | `Foundation` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | sdk-or-unresolved |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataTable.swift:9-9` | `RSDatabase` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/HTMLMetadata/Sources/HTMLMetadata/HTMLMetadataTable.swift:10-10` | `RSDatabaseObjC` | plain | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:10-10` | `Articles` | plain | `Images (Modules/Images/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:11-11` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/AuthorAvatarDownloader.swift:12-12` | `ActivityLog` | plain | `Images (Modules/Images/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Images/Sources/Images/ColorHash.swift:11-11` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ColorHash.swift:13-13` | `UIKit` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ColorHash.swift:15-15` | `WatchKit` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ColorHash.swift:17-17` | `AppKit` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/DownloadFailureTable.swift:8-8` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/DownloadFailureTable.swift:9-9` | `RSDatabase` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/DownloadFailureTable.swift:10-10` | `RSDatabaseObjC` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:10-10` | `os` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:11-11` | `CoreServices` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:12-12` | `Articles` | plain | `Images (Modules/Images/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:13-13` | `Account` | plain | `Images (Modules/Images/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:14-14` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:15-15` | `RSWeb` | plain | `Images (Modules/Images/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:16-16` | `HTMLMetadata` | plain | `Images (Modules/Images/Package.swift)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconDownloader.swift:17-17` | `UniformTypeIdentifiers` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FaviconGenerator.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FaviconGenerator.swift:10-10` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/FaviconGenerator.swift:11-11` | `Account` | plain | `Images (Modules/Images/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:10-10` | `Account` | plain | `Images (Modules/Images/Package.swift)` | `Account (Modules/Account/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:11-11` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:12-12` | `RSWeb` | plain | `Images (Modules/Images/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:13-13` | `HTMLMetadata` | plain | `Images (Modules/Images/Package.swift)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconDownloader.swift:14-14` | `ActivityLog` | plain | `Images (Modules/Images/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconURLTable.swift:8-8` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/FeedIconURLTable.swift:9-9` | `RSDatabase` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/FeedIconURLTable.swift:10-10` | `RSDatabaseObjC` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/HomePageFaviconTable.swift:8-8` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/HomePageFaviconTable.swift:9-9` | `RSDatabase` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/HomePageFaviconTable.swift:10-10` | `RSDatabaseObjC` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/IconImage.swift:10-10` | `AppKit` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/IconImage.swift:12-12` | `UIKit` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/IconImage.swift:14-14` | `os` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/IconImage.swift:15-15` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/ImageDownloader.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ImageDownloader.swift:10-10` | `os` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ImageDownloader.swift:11-11` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/ImageDownloader.swift:12-12` | `RSWeb` | plain | `Images (Modules/Images/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Images/Sources/Images/ImageDownloader.swift:13-13` | `ActivityLog` | plain | `Images (Modules/Images/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:8-8` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:9-9` | `os` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:10-10` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:11-11` | `RSDatabase` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/ImageMetadataDatabase.swift:12-12` | `RSDatabaseObjC` | plain | `Images (Modules/Images/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:9-9` | `Foundation` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:10-10` | `os` | plain | `Images (Modules/Images/Package.swift)` | sdk-or-unresolved |
| `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:11-11` | `ActivityLog` | plain | `Images (Modules/Images/Package.swift)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:12-12` | `RSCore` | plain | `Images (Modules/Images/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Images/Sources/Images/SingleFaviconDownloader.swift:13-13` | `RSWeb` | plain | `Images (Modules/Images/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:10-10` | `RSCore` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeed.swift:11-11` | `RSParser` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFeedChange.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurFolderChange.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurGenericCodingKeys.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurLoginResponse.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:10-10` | `RSCore` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStory.swift:11-11` | `RSParser` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:10-10` | `RSCore` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryHash.swift:11-11` | `RSParser` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/Models/NewsBlurStoryStatusChange.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlur.swift:8-8` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlur.swift:9-9` | `RSCore` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlur.swift:10-10` | `os` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller+Internal.swift:10-10` | `RSWeb` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:9-9` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:10-10` | `os` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:11-11` | `RSWeb` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/NewsBlurAPICaller.swift:12-12` | `Secrets` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/URLRequest+NewsBlur.swift:8-8` | `Foundation` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Sources/NewsBlur/URLRequest+NewsBlur.swift:9-9` | `RSWeb` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/NewsBlur/Sources/NewsBlur/URLRequest+NewsBlur.swift:10-10` | `Secrets` | plain | `NewsBlur (Modules/NewsBlur/Package.swift)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Modules/NewsBlur/Tests/NewsBlurTests/NewsBlurTests.swift:1-1` | `XCTest` | plain | `NewsBlurTests (Modules/NewsBlur/Package.swift)` | sdk-or-unresolved |
| `Modules/NewsBlur/Tests/NewsBlurTests/NewsBlurTests.swift:2-2` | `NewsBlur` | @testable | `NewsBlurTests (Modules/NewsBlur/Package.swift)` | `NewsBlur (Modules/NewsBlur/Package.swift)` |
| `Modules/RSCore/Sources/RSCore/AppConfig.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/FourCharCode.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/Keyboard.swift:9-9` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/KeyboardDelegateProtocol.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/MultilineTextFieldSizer.swift:11-11` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSAppearance+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSAppleEventDescriptor+RSCore.swift:9-9` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSImage+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSMenu+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSOutlineView+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSPasteboard+RSCore.swift:9-9` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSResponder+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSTableView+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSToolbar+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSView+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSWindow+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/NSWindowController+RSCore.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/PasteboardWriterOwner.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/RSAppMovementMonitor.swift:11-11` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/RSToolbarItem.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/SingleLineTextFieldSizer.swift:11-11` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/URLPasteboardWriter.swift:11-11` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/UserApp.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppKit/UtilityTableView.swift:9-9` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppNotifications.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/AppNotifications.swift:9-9` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Array+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/BatchUpdate.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/BinaryDiskCache.swift:10-10` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Blocks.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Bundle+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/CGImage+RSCore.swift:9-9` | `CoreGraphics` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Cache.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Cache.swift:9-9` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Calendar+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/CoalescingQueue.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Comparing.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Data+RSCore.swift:10-10` | `CryptoKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Date+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/DateFormatter+RSCore.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/DisplayNameProvider.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/FileManager+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Geometry.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Logging.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Logging.swift:9-9` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MacroProcessor.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MainThreadBlockOperation.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MainThreadOperation.swift:10-10` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MainThreadOperationQueue.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MemoryPressureMonitor.swift:10-10` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/MemoryPressureMonitor.swift:11-11` | `Dispatch` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/NotificationCenter+RSCore.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/OPMLRepresentable.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Platform.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Platform.swift:10-10` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSImage.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSImage.swift:10-10` | `UniformTypeIdentifiers` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSImage.swift:11-11` | `os` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSImage.swift:14-14` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSImage.swift:20-20` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSProgress.swift:8-8` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSScreen.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/RSScreen.swift:22-22` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/Renamable.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/SendToBlogEditorApp.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/SendToCommand.swift:10-10` | `AppKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/SendToCommand.swift:14-14` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/String+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/String+RSCore.swift:10-10` | `CryptoKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/Animations.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/CroppingPreviewParameters.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/ImageHeaderView.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicImageView.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/NonIntrinsicLabel.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/PoppableGestureRecognizerDelegate.swift:12-12` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:10-10` | `SwiftUI` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/SafariView+RSCore.swift:11-11` | `SafariServices` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIBarButtonItem+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UICollectionView+RSCore.swift:11-11` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UICollectionView+RSCore.swift:12-12` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIFont+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIPageViewController+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIResponder+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIStoryboard+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UITableView+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIView+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIViewController+RSCore.swift:12-12` | `SwiftUI` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UIKit/UIWindow+RSCore.swift:11-11` | `UIKit` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/URL+RSCore.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UndoableCommand.swift:9-9` | `Foundation` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCore/UniformTypeIdentifiers+RSCore.swift:9-9` | `UniformTypeIdentifiers` | plain | `RSCore (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCoreResources/AppKit/IndeterminateProgressWindowController.swift:10-10` | `AppKit` | plain | `RSCoreResources (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:10-10` | `AppKit` | plain | `RSCoreResources (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Sources/RSCoreResources/AppKit/WebViewWindowController.swift:11-11` | `WebKit` | plain | `RSCoreResources (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/CGImageLuminanceTests.swift:8-8` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/CGImageLuminanceTests.swift:9-9` | `CoreGraphics` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/CGImageLuminanceTests.swift:10-10` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespacePerformanceTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespacePerformanceTests.swift:10-10` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespaceTests.swift:9-9` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/CollapsingWhitespaceTests.swift:10-10` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/Data+RSCoreTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/Data+RSCoreTests.swift:10-10` | `Foundation` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/Data+RSCoreTests.swift:11-11` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/HMACTests.swift:8-8` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/HMACTests.swift:9-9` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/MD5PerformanceTests.swift:8-8` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MD5PerformanceTests.swift:9-9` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/MD5Tests.swift:8-8` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MD5Tests.swift:9-9` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/MacroProcessorTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MacroProcessorTests.swift:10-10` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift:10-10` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/MultilineTextFieldSizerTests.swift:10-10` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MultilineTextFieldSizerTests.swift:11-11` | `AppKit` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/MultilineTextFieldSizerTests.swift:12-12` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/SingleLineTextFieldSizerTests.swift:10-10` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/SingleLineTextFieldSizerTests.swift:11-11` | `AppKit` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/SingleLineTextFieldSizerTests.swift:12-12` | `RSCore` | @testable | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSCore/Tests/RSCoreTests/String+RSCoreTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/StripHTMLPerformanceTests.swift:9-9` | `XCTest` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/StripHTMLTests.swift:9-9` | `Foundation` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/StripHTMLTests.swift:10-10` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/URL+RSCoreTests.swift:8-8` | `Foundation` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/URL+RSCoreTests.swift:9-9` | `Testing` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | sdk-or-unresolved |
| `Modules/RSCore/Tests/RSCoreTests/URL+RSCoreTests.swift:10-10` | `RSCore` | plain | `RSCoreTests (Modules/RSCore/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/Database.swift:9-9` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/Database.swift:10-10` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:9-9` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:10-10` | `os` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:11-11` | `SQLite3` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseQueue.swift:12-12` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:9-9` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/DatabaseTable.swift:10-10` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:8-8` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:9-9` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/FMDatabase+Extras.swift:10-10` | `os` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:8-8` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/FMResultSet+Extras.swift:9-9` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Sources/RSDatabase/Logging.swift:8-8` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/RSDatabaseInfoTable.swift:8-8` | `Foundation` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Sources/RSDatabase/RSDatabaseInfoTable.swift:9-9` | `RSDatabaseObjC` | plain | `RSDatabase (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift:8-8` | `Testing` | plain | `RSDatabaseTests (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift:9-9` | `Foundation` | plain | `RSDatabaseTests (Modules/RSDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift:10-10` | `RSDatabase` | plain | `RSDatabaseTests (Modules/RSDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/RSDatabase/Tests/RSDatabaseTests/DatabaseTests.swift:11-11` | `RSDatabaseObjC` | plain | `RSDatabaseTests (Modules/RSDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/RSParser/Sources/RSParser/Feeds/Data+ProbablyFormat.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/FeedParser.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/FeedParserError.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/FeedType.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/JSON/RSSInJSONParser.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/JSON/RSSInJSONParser.swift:10-10` | `RSCore` | plain | `RSParser (Modules/RSParser/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedAttachment.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedAuthor.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedFeed.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedHub.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/ParsedItem.swift:10-10` | `Tidemark` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/XML/AtomParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/XML/OPMLParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/XML/RSSItem.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Feeds/XML/RSSItem.swift:9-9` | `RSCore` | plain | `RSParser (Modules/RSParser/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSParser/Sources/RSParser/Feeds/XML/RSSParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/HTML/HTMLLinkParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:8-8` | `CoreGraphics` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadata.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/HTML/HTMLMetadataParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/HTML/HTMLRelativeURLResolver.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/JSON/JSONTypes.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/JSON/JSONUtilities.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/OPML/OPMLError.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/ParserData.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Utilities/DateParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/Utilities/String+RSParser.swift:9-9` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/XML/XMLEncoding.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/XML/XMLEntities.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Sources/RSParser/XML/XMLSAXParser.swift:8-8` | `Foundation` | plain | `RSParser (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypePerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypePerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypeTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypeTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/FeedParserTypeTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/JSONFeedParserTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/JSON/RSSInJSONParserTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/AtomParserTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Feeds/XML/RSSParserTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLLinkTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataPerformanceTests.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataTests.swift:9-9` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataTests.swift:10-10` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLMetadataTests.swift:11-11` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLRelativeURLResolverTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLRelativeURLResolverTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/HTML/HTMLRelativeURLResolverTests.swift:10-10` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/TestHelpers.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/TestHelpers.swift:9-9` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserPerformanceTests.swift:8-8` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserPerformanceTests.swift:9-9` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingPerformanceTests.swift:9-9` | `XCTest` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingPerformanceTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/EntityDecodingTests.swift:10-10` | `RSParser` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLASCIITests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLASCIITests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLASCIITests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLAttributesTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLAttributesTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLAttributesTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEntitiesTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEntitiesTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLEntitiesTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLNamespaceContextTests.swift:8-8` | `Foundation` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLNamespaceContextTests.swift:9-9` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLNamespaceContextTests.swift:10-10` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLSAXParserTests.swift:8-8` | `Testing` | plain | `RSParserTests (Modules/RSParser/Package.swift)` | sdk-or-unresolved |
| `Modules/RSParser/Tests/RSParserTests/XML/XMLSAXParserTests.swift:9-9` | `RSParser` | @testable | `RSParserTests (Modules/RSParser/Package.swift)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Modules/RSTree/Sources/RSTree/NSOutlineView+RSTree.swift:11-11` | `AppKit` | plain | `RSTree (Modules/RSTree/Package.swift)` | sdk-or-unresolved |
| `Modules/RSTree/Sources/RSTree/Node.swift:9-9` | `Foundation` | plain | `RSTree (Modules/RSTree/Package.swift)` | sdk-or-unresolved |
| `Modules/RSTree/Sources/RSTree/NodePath.swift:9-9` | `Foundation` | plain | `RSTree (Modules/RSTree/Package.swift)` | sdk-or-unresolved |
| `Modules/RSTree/Sources/RSTree/TopLevelRepresentedObject.swift:9-9` | `Foundation` | plain | `RSTree (Modules/RSTree/Package.swift)` | sdk-or-unresolved |
| `Modules/RSTree/Sources/RSTree/TreeController.swift:9-9` | `Foundation` | plain | `RSTree (Modules/RSTree/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/CacheControlInfo.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/Dictionary+RSWeb.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/DownloadCache.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/DownloadCache.swift:9-9` | `RSCore` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Sources/RSWeb/DownloadResponse.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:10-10` | `os` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift:11-11` | `RSCore` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Sources/RSWeb/Downloader.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/Downloader.swift:10-10` | `os` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/Downloader.swift:11-11` | `RSCore` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Sources/RSWeb/HTTPConditionalGetInfo.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPDateInfo.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPLinkPagingInfo.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPMethod.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPRequestHeader.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPResponse429.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPResponseCode.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/HTTPResponseHeader.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:10-10` | `AppKit` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/MacWebBrowser.swift:11-11` | `UniformTypeIdentifiers` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/MimeType.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:9-9` | `Network` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/NetworkMonitor.swift:10-10` | `os` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/SpecialCases.swift:9-9` | `os` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/String+RSWeb.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/URL+RSWeb.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/URLComponents+RSWeb.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/URLRequest+RSWeb.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/URLResponse+RSWeb.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/UserAgent.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:8-8` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/WebServices/TestingURLProtocol.swift:9-9` | `os` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+Webservice.swift:10-10` | `RSCore` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Sources/RSWeb/WebServices/URLSession+WebserviceJSON.swift:9-9` | `Foundation` | plain | `RSWeb (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/DictionaryTests.swift:9-9` | `XCTest` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/DictionaryTests.swift:10-10` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/DownloadSession429Tests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/DownloadSession429Tests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/DownloadSession429Tests.swift:10-10` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/HTTPLinkPagingInfoTests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/HTTPLinkPagingInfoTests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/HTTPLinkPagingInfoTests.swift:10-10` | `RSWeb` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/MacWebBrowserTests.swift:10-10` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/MacWebBrowserTests.swift:11-11` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/SpecialCasesTests.swift:8-8` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/SpecialCasesTests.swift:9-9` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/SpecialCasesTests.swift:10-10` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/StringTests.swift:9-9` | `XCTest` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/StringTests.swift:10-10` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolIsolationTests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolIsolationTests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolIsolationTests.swift:10-10` | `RSCore` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolIsolationTests.swift:11-11` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolMethodMatchingTests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolMethodMatchingTests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolMethodMatchingTests.swift:10-10` | `RSCore` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolMethodMatchingTests.swift:11-11` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolRequestCountTests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolRequestCountTests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolRequestCountTests.swift:10-10` | `RSCore` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/TestingURLProtocolRequestCountTests.swift:11-11` | `RSWeb` | @testable | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/RSWeb/Tests/RSWebTests/URLPreparedForOpeningTests.swift:8-8` | `Foundation` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/URLPreparedForOpeningTests.swift:9-9` | `Testing` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | sdk-or-unresolved |
| `Modules/RSWeb/Tests/RSWebTests/URLPreparedForOpeningTests.swift:10-10` | `RSWeb` | plain | `RSWebTests (Modules/RSWeb/Package.swift)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Modules/Secrets/Sources/Secrets/Credentials.swift:9-9` | `Foundation` | plain | `Secrets (Modules/Secrets/Package.swift)` | sdk-or-unresolved |
| `Modules/Secrets/Sources/Secrets/Credentials.swift:10-10` | `Security` | plain | `Secrets (Modules/Secrets/Package.swift)` | sdk-or-unresolved |
| `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:9-9` | `Foundation` | plain | `Secrets (Modules/Secrets/Package.swift)` | sdk-or-unresolved |
| `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:10-10` | `os` | plain | `Secrets (Modules/Secrets/Package.swift)` | sdk-or-unresolved |
| `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:11-11` | `Security` | plain | `Secrets (Modules/Secrets/Package.swift)` | sdk-or-unresolved |
| `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:12-12` | `RSCore` | plain | `Secrets (Modules/Secrets/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/Secrets/Sources/Secrets/CredentialsManager.swift:13-13` | `ErrorLog` | plain | `Secrets (Modules/Secrets/Package.swift)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:9-9` | `Foundation` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:10-10` | `os` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:11-11` | `RSCore` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:12-12` | `RSDatabase` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift:13-13` | `RSDatabaseObjC` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabaseError.swift:8-8` | `Foundation` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabaseError.swift:9-9` | `RSDatabaseObjC` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:9-9` | `Foundation` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:10-10` | `Articles` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatus.swift:11-11` | `RSDatabase` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatusTable.swift:9-9` | `Foundation` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatusTable.swift:10-10` | `Articles` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `Articles (Modules/Articles/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatusTable.swift:11-11` | `RSDatabase` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Sources/SyncDatabase/SyncStatusTable.swift:12-12` | `RSDatabaseObjC` | plain | `SyncDatabase (Modules/SyncDatabase/Package.swift)` | `RSDatabaseObjC (Modules/RSDatabase/Package.swift)` |
| `Modules/SyncDatabase/Tests/SyncDatabaseTests/SyncStatusTableTests.swift:8-8` | `Foundation` | plain | `SyncDatabaseTests (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Tests/SyncDatabaseTests/SyncStatusTableTests.swift:9-9` | `Testing` | plain | `SyncDatabaseTests (Modules/SyncDatabase/Package.swift)` | sdk-or-unresolved |
| `Modules/SyncDatabase/Tests/SyncDatabaseTests/SyncStatusTableTests.swift:10-10` | `SyncDatabase` | plain | `SyncDatabaseTests (Modules/SyncDatabase/Package.swift)` | `SyncDatabase (Modules/SyncDatabase/Package.swift)` |
| `Shared/AccountStats/AccountStatsViewModel.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AccountStats/AccountStatsViewModel.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/AccountStats/AccountStatsViewModel.swift:10-10` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/AccountStats/AccountStatsViewModel.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/AccountType+Helpers.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AccountType+Helpers.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/AccountType+Helpers.swift:12-12` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AccountType+Helpers.swift:14-14` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AccountType+Helpers.swift:16-16` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:10-10` | `CoreSpotlight` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:11-11` | `CoreServices` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Activity/ActivityManager.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Activity/ActivityManager.swift:14-14` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Activity/ActivityManager.swift:15-15` | `Intents` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:16-16` | `UniformTypeIdentifiers` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Activity/ActivityManager.swift:17-17` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Activity/ActivityType.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ActivityLog/ActivityLogViewModel.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ActivityLog/ActivityLogViewModel.swift:9-9` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AppDelegate+Shared.swift:9-9` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:10-10` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:11-11` | `ErrorLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:12-12` | `HTMLMetadata` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:13-13` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/AppDelegate+Shared.swift:14-14` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/AppNotifications.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/AppNotifications.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Article Extractor/ArticleExtractor.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Extractor/ArticleExtractor.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Article Extractor/ArticleExtractor.swift:11-11` | `Secrets` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `Shared/Article Extractor/ExtractedArticle.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/ArticleRenderer.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/ArticleRenderer.swift:11-11` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/ArticleRenderer.swift:13-13` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Article Rendering/ArticleRenderer.swift:14-14` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Article Rendering/ArticleRenderer.swift:15-15` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Article Rendering/ArticleRenderingSpecialCases.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/ArticleRenderingSpecialCases.swift:10-10` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Shared/Article Rendering/ArticleRenderingSpecialCases.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Article Rendering/ArticleTextSize.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/WebViewConfiguration.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/WebViewConfiguration.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Article Rendering/WebViewConfiguration.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/WebViewConfiguration.swift:12-12` | `WebKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Article Rendering/WebViewConfiguration.swift:13-13` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Shared/Article Rendering/WebViewConfiguration.swift:14-14` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/ArticleSpecifier.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleSpecifier.swift:9-9` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/ArticleStyles/ArticleTheme+Notifications.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleTheme.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemeDownloader.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemeDownloader.swift:10-10` | `Zip` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemeDownloader.swift:11-11` | `RSWeb` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Shared/ArticleStyles/ArticleThemePlist.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemesManager.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemesManager.swift:10-10` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ArticleStyles/ArticleThemesManager.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Assets.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Assets.swift:12-12` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Assets.swift:15-15` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Assets.swift:16-16` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Assets.swift:17-17` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Commands/DeleteCommand.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Commands/DeleteCommand.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Commands/DeleteCommand.swift:11-11` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Shared/Commands/DeleteCommand.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Commands/DeleteCommand.swift:13-13` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Commands/MarkCommandValidationStatus.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Commands/MarkStatusCommand.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Commands/MarkStatusCommand.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Commands/MarkStatusCommand.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/CurrentActivity/CurrentActivityViewModel.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/CurrentActivity/CurrentActivityViewModel.swift:9-9` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Shared/Dinosaurs/DinosaursViewModel.swift:8-8` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Dinosaurs/DinosaursViewModel.swift:9-9` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Dinosaurs/DinosaursViewModel.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Dinosaurs/DinosaursViewModel.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Exporters/OPMLExporter.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Exporters/OPMLExporter.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Exporters/OPMLExporter.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/ExtensionPoints/SendToMarsEditCommand.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ExtensionPoints/SendToMarsEditCommand.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/ExtensionPoints/SendToMarsEditCommand.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/ExtensionPoints/SendToMicroBlogCommand.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ExtensionPoints/SendToMicroBlogCommand.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/ExtensionPoints/SendToMicroBlogCommand.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/AddFeedDefaultContainer.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/AddFeedDefaultContainer.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Extensions/ArticleStringFormatter.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/ArticleStringFormatter.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Extensions/ArticleStringFormatter.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/ArticleStringFormatter.swift:12-12` | `RSParser` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Shared/Extensions/ArticleUtilities.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/ArticleUtilities.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/ArticleUtilities.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Extensions/ArticleUtilities.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Extensions/ArticleUtilities.swift:13-13` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Extensions/CacheCleaner.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/CacheCleaner.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/CacheCleaner.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/IconImageView.swift:11-11` | `SwiftUI` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/IconImageView.swift:12-12` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Extensions/IconImageView.swift:14-14` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/IconImageView.swift:17-17` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/NSAttributedString+Extensions.swift:10-10` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/NSAttributedString+Extensions.swift:13-13` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/NSAttributedString+Extensions.swift:16-16` | `RSParser` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Shared/Extensions/Node+Extensions.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/Node+Extensions.swift:10-10` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Shared/Extensions/Node+Extensions.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Extensions/Node+Extensions.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/RSImage+Extensions.swift:9-9` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/RSImage+Extensions.swift:10-10` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Extensions/RSImage+Extensions.swift:12-12` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/RSImage+Extensions.swift:14-14` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/SmallIconProvider.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Extensions/SmallIconProvider.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Extensions/SmallIconProvider.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Extensions/SmallIconProvider.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Extensions/SmallIconProvider.swift:13-13` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/HelpURL.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/IconImageCache.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/IconImageCache.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/IconImageCache.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/IconImageCache.swift:12-12` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/IconImageCache.swift:13-13` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Importers/DefaultFeedsImporter.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Importers/DefaultFeedsImporter.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Importers/DefaultFeedsImporter.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Settings/AddCloudKitAccount.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Settings/AddCloudKitAccount.swift:11-11` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Settings/AddCloudKitAccount.swift:14-14` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Settings/AddCloudKitAccount.swift:16-16` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/ShareExtension/ExtensionContainers.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionContainers.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/ShareExtension/ExtensionContainersFile.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionContainersFile.swift:10-10` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionContainersFile.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/ShareExtension/ExtensionContainersFile.swift:12-12` | `RSParser` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Shared/ShareExtension/ExtensionContainersFile.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift:11-11` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/ShareExtension/ShareDefaultContainer.swift:9-9` | `Foundation` | plain | `NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/PseudoFeed.swift:11-11` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/PseudoFeed.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/PseudoFeed.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/PseudoFeed.swift:14-14` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/PseudoFeed.swift:22-22` | `UIKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/PseudoFeed.swift:23-23` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/PseudoFeed.swift:24-24` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/PseudoFeed.swift:25-25` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:13-13` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:13-13` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/SmartFeeds/SmartFeed.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SmartFeed.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SmartFeed.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/SmartFeed.swift:12-12` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/SmartFeed.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/SmartFeed.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SmartFeedDelegate.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift:12-12` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift:13-13` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedPasteboardWriter.swift:9-9` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SmartFeedPasteboardWriter.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedPasteboardWriter.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedsController.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/SmartFeedsController.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/SmartFeedsController.swift:11-11` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:12-12` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:12-12` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift:14-14` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/SmartFeeds/UnreadFeed.swift:10-10` | `AppKit` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/UnreadFeed.swift:12-12` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/SmartFeeds/UnreadFeed.swift:14-14` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/SmartFeeds/UnreadFeed.swift:15-15` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/SmartFeeds/UnreadFeed.swift:16-16` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/SmartFeeds/UnreadFeed.swift:17-17` | `ArticlesDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ArticlesDatabase (Modules/ArticlesDatabase/Package.swift)` |
| `Shared/SmartFeeds/UnreadFeed.swift:18-18` | `Images` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `Shared/Timeline/ArticleArray.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timeline/ArticleArray.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Timeline/ArticleSortParameters.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timeline/ArticleSorter.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timeline/ArticleSorter.swift:10-10` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Timeline/FetchRequestOperation.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timeline/FetchRequestOperation.swift:10-10` | `os` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timeline/FetchRequestOperation.swift:11-11` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Timeline/FetchRequestOperation.swift:12-12` | `RSDatabase` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSDatabase (Modules/RSDatabase/Package.swift)` |
| `Shared/Timeline/FetchRequestOperation.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Timeline/FetchRequestOperation.swift:14-14` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Timeline/FetchRequestOperation.swift:15-15` | `ErrorLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `Shared/Timeline/FetchRequestQueue.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timer/AccountRefreshTimer.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timer/AccountRefreshTimer.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Timer/AccountRefreshTimer.swift:11-11` | `ActivityLog` | plain | `NetNewsWire (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `Shared/Timer/ArticleStatusSyncTimer.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Timer/ArticleStatusSyncTimer.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Timer/RefreshInterval.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Tree/FolderTreeControllerDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Tree/FolderTreeControllerDelegate.swift:10-10` | `RSCore` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Tree/FolderTreeControllerDelegate.swift:11-11` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Shared/Tree/FolderTreeControllerDelegate.swift:12-12` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Tree/FolderTreeControllerDelegate.swift:13-13` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Tree/SidebarTreeControllerDelegate.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Tree/SidebarTreeControllerDelegate.swift:10-10` | `RSTree` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `Shared/Tree/SidebarTreeControllerDelegate.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Tree/SidebarTreeControllerDelegate.swift:12-12` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/UserInfoKey.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/UserNotifications/UserNotificationManager.swift:9-9` | `Foundation` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/UserNotifications/UserNotificationManager.swift:10-10` | `Account` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/UserNotifications/UserNotificationManager.swift:11-11` | `Articles` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/UserNotifications/UserNotificationManager.swift:12-12` | `UserNotifications` | plain | `NetNewsWire (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetData.swift:9-9` | `Foundation` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataDecoder.swift:9-9` | `Foundation` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataEncoder.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataEncoder.swift:10-10` | `WidgetKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataEncoder.swift:11-11` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataEncoder.swift:12-12` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Shared/Widget/WidgetDataEncoder.swift:13-13` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Shared/Widget/WidgetDataEncoder.swift:14-14` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Shared/Widget/WidgetDataEncoder.swift:15-15` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `Shared/Widget/WidgetDeepLinks.swift:9-9` | `Foundation` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift:8-8` | `Testing` | plain | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift:10-10` | `NetNewsWire` | @testable | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift:8-8` | `Testing` | plain | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift:10-10` | `NetNewsWire` | @testable | `NetNewsWire-iOSTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift:8-8` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift:9-9` | `Testing` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift:11-11` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ArticleSorterTests.swift:9-9` | `Articles` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Tests/NetNewsWireTests/ArticleSorterTests.swift:10-10` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleSorterTests.swift:11-11` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleSorterTests.swift:13-13` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:9-9` | `Articles` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:10-10` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:11-11` | `RSCore` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:12-12` | `RSParser` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `RSParser (Modules/RSParser/Package.swift)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:13-13` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift:15-15` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift:9-9` | `Articles` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift:10-10` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift:11-11` | `Testing` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift:13-13` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift:10-10` | `Testing` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift:12-12` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLPerformanceTests.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLPerformanceTests.swift:10-10` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLPerformanceTests.swift:12-12` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift:10-10` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift:12-12` | `AppKit` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift:14-14` | `UIKit` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift:17-17` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/SanitizedTitlePerformanceTests.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SanitizedTitlePerformanceTests.swift:10-10` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SanitizedTitlePerformanceTests.swift:12-12` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/SanitizedTitleTests.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SanitizedTitleTests.swift:10-10` | `Testing` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SanitizedTitleTests.swift:12-12` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ScriptingTests/AppleScriptXCTestCase.swift:9-9` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ScriptingTests/NSAppleEventDescriptor+UserRecordFields.swift:9-9` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ScriptingTests/ScriptingTests.swift:9-9` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SharingTests.swift:9-9` | `Articles` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `Tests/NetNewsWireTests/SharingTests.swift:10-10` | `XCTest` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/SharingTests.swift:12-12` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Tests/NetNewsWireTests/ThemeUnzipTests.swift:8-8` | `Foundation` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ThemeUnzipTests.swift:9-9` | `Testing` | plain | `NetNewsWireTests (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Tests/NetNewsWireTests/ThemeUnzipTests.swift:11-11` | `NetNewsWire` | @testable | `NetNewsWireTests (NetNewsWire.xcodeproj)` | `NetNewsWire (NetNewsWire.xcodeproj)` |
| `Widget/Shared Views/ArticleItemView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Shared Views/ArticleItemView.swift:10-10` | `RSWeb` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `Widget/Shared Views/SizeCategories.swift:9-9` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/TimelineProvider.swift:9-9` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/TimelineProvider.swift:10-10` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/LockScreenSummaryWidget.swift:9-9` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/LockScreenSummaryWidget.swift:10-10` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/StarredWidget.swift:9-9` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/StarredWidget.swift:10-10` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/TodayWidget.swift:9-9` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/TodayWidget.swift:10-10` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/UnreadWidget.swift:9-9` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/UnreadWidget.swift:10-10` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/Widget Views/WidgetLayout.swift:9-9` | `Foundation` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/WidgetBundle.swift:9-9` | `WidgetKit` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `Widget/WidgetBundle.swift:10-10` | `SwiftUI` | plain | `NetNewsWire iOS Widget Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `buildscripts/VerifyNoBS.swift:14-14` | `Darwin` | plain | — | sdk-or-unresolved |
| `buildscripts/VerifyNoBS.swift:15-15` | `Foundation` | plain | — | sdk-or-unresolved |
| `iOS/Account/AccountIconHeader.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/AccountIconHeader.swift:9-9` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Account/AccountNotificationInspectorView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/AccountNotificationInspectorView.swift:10-10` | `UserNotifications` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/AccountNotificationInspectorView.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Account/AccountNotificationInspectorView.swift:12-12` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/Account/AccountSheetFooter.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/CloudKitAccountView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/CloudKitAccountView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Account/CloudKitAccountView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Account/CredentialsAccountView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/CredentialsAccountView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Account/CredentialsAccountView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Account/CredentialsAccountView.swift:11-11` | `Secrets` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `iOS/Account/LocalAccountView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Account/LocalAccountView.swift:9-9` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/AccountStats/AccountStatsView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AccountStats/AccountStatsView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AccountStats/AccountStatsView.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/AccountStats/AccountStatsView.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Add/AddFeedContainerPickerView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Add/AddFeedContainerPickerView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Add/AddFeedContainerPickerView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Add/AddFeedView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Add/AddFeedView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Add/AddFeedView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Add/AddFolderView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Add/AddFolderView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Add/AddFolderView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/AppDefaults.swift:9-9` | `RSCore` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/AppDefaults.swift:10-10` | `UIKit` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDefaults.swift:11-11` | `os` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDefaults.swift:12-12` | `Account` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/AppDefaults.swift:13-13` | `Articles` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/AppDefaults.swift:14-14` | `Images` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj), NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/AppDelegate.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDelegate.swift:10-10` | `BackgroundTasks` | @preconcurrency | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDelegate.swift:11-11` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDelegate.swift:12-12` | `WidgetKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppDelegate.swift:13-13` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/AppDelegate.swift:14-14` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/AppDelegate.swift:15-15` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/AppDelegate.swift:16-16` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/AppDelegate.swift:17-17` | `Secrets` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Secrets (Modules/Secrets/Package.swift)` |
| `iOS/AppDelegate.swift:18-18` | `ErrorLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `iOS/AppDelegate.swift:19-19` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/AppIntents/AddFeedAppIntent.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppIntents/AddFeedAppIntent.swift:10-10` | `AppIntents` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/AppIntents/NetNewsWireAppShortcuts.swift:9-9` | `AppIntents` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleExtractorButton.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleIconSchemeHandler.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleIconSchemeHandler.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleIconSchemeHandler.swift:11-11` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/Article/ArticleSearchBar.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleViewController.swift:10-10` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleViewController.swift:11-11` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleViewController.swift:12-12` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ArticleViewController.swift:13-13` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Article/ArticleViewController.swift:14-14` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Article/ArticleViewController.swift:15-15` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/Article/ContextMenuPreviewViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ContextMenuPreviewViewController.swift:10-10` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/Article/FindInArticleActivity.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ImageScrollView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ImageTransition.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/ImageViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/OpenInSafariActivity.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/PreloadedWebView.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/PreloadedWebView.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewController.swift:10-10` | `WebKit` | @preconcurrency | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewController.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Article/WebViewController.swift:12-12` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/Article/WebViewController.swift:13-13` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Article/WebViewController.swift:14-14` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/Article/WebViewController.swift:15-15` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewController.swift:16-16` | `MessageUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewController.swift:17-17` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/Article/WebViewFullscreenKeeper.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewFullscreenKeeper.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewFullscreenKeeper.swift:11-11` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewProvider.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewProvider.swift:10-10` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WebViewProvider.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Article/WebViewProvider.swift:12-12` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WrapperScriptMessageHandler.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Article/WrapperScriptMessageHandler.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ArticleActivityItemSource.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/CurrentActivity/CurrentActivityView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/CurrentActivity/CurrentActivityView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/CurrentActivity/CurrentActivityView.swift:10-10` | `ActivityLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `iOS/ErrorHandler.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ErrorHandler.swift:10-10` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ErrorHandler.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/HidingReadArticlesState.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/HidingReadArticlesState.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/IconView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/IconView.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/IconView.swift:11-11` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/Inspector/AccountInspectorViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/AccountInspectorViewController.swift:10-10` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/AccountInspectorViewController.swift:11-11` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/AccountInspectorViewController.swift:12-12` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Inspector/AccountInspectorViewController.swift:13-13` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Inspector/FeedInspectorViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/FeedInspectorViewController.swift:10-10` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/FeedInspectorViewController.swift:11-11` | `UserNotifications` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Inspector/FeedInspectorViewController.swift:12-12` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Inspector/FeedInspectorViewController.swift:13-13` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Inspector/FeedInspectorViewController.swift:14-14` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/Inspector/InspectorIconHeaderView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/KeyboardManager.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionHeaderReusableView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionHeaderReusableView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift:12-12` | `RSTree` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift:13-13` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewFolderCell.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewFolderCell.swift:10-10` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainFeed/Collection View Cells/MainFeedRowIdentifier.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:12-12` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:13-13` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:14-14` | `RSTree` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:15-15` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:16-16` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift:17-17` | `UniformTypeIdentifiers` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:10-10` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:12-12` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:13-13` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:14-14` | `RSTree` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:15-15` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:16-16` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift:17-17` | `UniformTypeIdentifiers` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:10-10` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:11-11` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:12-12` | `UniformTypeIdentifiers` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:13-13` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:14-14` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:15-15` | `RSTree` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:16-16` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:17-17` | `HTMLMetadata` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:18-18` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:19-19` | `ActivityLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:20-20` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift:21-21` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainFeed/RefreshProgressView.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainFeed/RefreshProgressView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCell.swift:8-8` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/Cell/MainTimelineCell.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCell.swift:10-10` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCellData.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/Cell/MainTimelineCellData.swift:10-10` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCellData.swift:11-11` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift:11-11` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainTimeline/Cell/MultilineUILabelSizer.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/Cell/SingleLineUILabelSizer.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/Cell/StringSize+Extensions.swift:8-8` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MainTimelineDataSource.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:10-10` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:11-11` | `WebKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:12-12` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:13-13` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:14-14` | `HTMLMetadata` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `HTMLMetadata (Modules/HTMLMetadata/Package.swift)` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:15-15` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:16-16` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift:17-17` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/MainTimeline/MarkAsReadAlertController.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/MainTimeline/MarkAsReadAlertController.swift:10-10` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/RootSplitViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/RootSplitViewController.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/SceneCoordinator.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneCoordinator.swift:10-10` | `os` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneCoordinator.swift:11-11` | `UserNotifications` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneCoordinator.swift:12-12` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/SceneCoordinator.swift:13-13` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/SceneCoordinator.swift:14-14` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/SceneCoordinator.swift:15-15` | `RSTree` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSTree (Modules/RSTree/Package.swift)` |
| `iOS/SceneCoordinator.swift:16-16` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneCoordinator.swift:17-17` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneCoordinator.swift:18-18` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/SceneDelegate.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneDelegate.swift:10-10` | `UserNotifications` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/SceneDelegate.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/AboutContributor.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/AboutCreditView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/AboutView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ActivityLogView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ActivityLogView.swift:9-9` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/ActivityLogView.swift:10-10` | `ActivityLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `iOS/Settings/ActivityLogView.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/AddAccountView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/AddAccountView.swift:9-9` | `AuthenticationServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/AddAccountView.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/AddAccountView.swift:11-11` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/ArticleThemeImporter.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ArticleThemeImporter.swift:10-10` | `RSWeb` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSWeb (Modules/RSWeb/Package.swift)` |
| `iOS/Settings/ArticleThemesTableViewController.swift:9-9` | `Foundation` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ArticleThemesTableViewController.swift:10-10` | `UniformTypeIdentifiers` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ArticleThemesTableViewController.swift:11-11` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/CloudKitStatsView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/CloudKitStatsView.swift:9-9` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/CloudKitStatsView.swift:10-10` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/ColorPaletteTableViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/DinosaurRowView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/DinosaursView.swift:9-9` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/DinosaursView.swift:10-10` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/ErrorLogView.swift:8-8` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/ErrorLogView.swift:9-9` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/ErrorLogView.swift:10-10` | `ErrorLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ErrorLog (Modules/ErrorLog/Package.swift)` |
| `iOS/Settings/ErrorLogView.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/SettingsComboTableViewCell.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:10-10` | `CoreServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:11-11` | `SafariServices` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:12-12` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:13-13` | `UniformTypeIdentifiers` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/SettingsViewController.swift:14-14` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/Settings/SettingsViewController.swift:15-15` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/Settings/SettingsViewController.swift:16-16` | `ActivityLog` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `ActivityLog (Modules/ActivityLog/Package.swift)` |
| `iOS/Settings/TickMarkSlider.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/TimelineCustomizerCell.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/TimelineCustomizerCell.swift:10-10` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/Settings/TimelineCustomizerCollectionViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/Settings/TimelineCustomizerCollectionViewController.swift:10-10` | `Articles` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Articles (Modules/Articles/Package.swift)` |
| `iOS/Settings/TimelineCustomizerCollectionViewController.swift:11-11` | `Images` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Images (Modules/Images/Package.swift)` |
| `iOS/ShareExtension/ShareFolderPickerCell.swift:9-9` | `UIKit` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ShareExtension/ShareFolderPickerController.swift:9-9` | `UIKit` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ShareExtension/ShareFolderPickerController.swift:10-10` | `Account` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/ShareExtension/ShareFolderPickerController.swift:11-11` | `RSCore` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/ShareExtension/ShareViewController.swift:9-9` | `UIKit` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ShareExtension/ShareViewController.swift:10-10` | `UniformTypeIdentifiers` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/ShareExtension/ShareViewController.swift:11-11` | `Account` | plain | `NetNewsWire iOS Share Extension (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/TitleActivityItemSource.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/UIActivityViewController+Extras.swift:11-11` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/UIViewController+Extras.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/UIViewController+Extras.swift:10-10` | `SwiftUI` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/UIViewController+Extras.swift:11-11` | `RSCore` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `RSCore (Modules/RSCore/Package.swift)` |
| `iOS/UIKit Extensions/UIViewController+Extras.swift:12-12` | `Account` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | `Account (Modules/Account/Package.swift)` |
| `iOS/UIKit Extensions/VibrantButton.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/VibrantLabel.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |
| `iOS/UIKit Extensions/VibrantTableViewCell.swift:9-9` | `UIKit` | plain | `NetNewsWire-iOS (NetNewsWire.xcodeproj)` | sdk-or-unresolved |

## Membership

| file | target | route | conditional | declared at |
|---|---|---|---|---|
| `Mac/About/AboutWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/About/LinkLabel.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/About/LinksTextView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/AccountStats/AccountStatsWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/ActivityLog/ActivityLogWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/AppDefaults.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/AppDefaults.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:334-334` |
| `Mac/AppDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Browser.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpContentView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpStatusView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CleanUp/CloudKitStatsCleanUpViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CloudKitStatsLayout.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CloudKitStatsToolbarView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CloudKitStatsViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/CloudKitStatsWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanContentView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanStatusView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CloudKitStats/Scan/CloudKitStatsScanViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CrashReporter/CrashReportWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CrashReporter/CrashReporter.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/CurrentActivity/CurrentActivityWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Dinosaurs/DinosaursWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/ErrorHandler.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/ErrorLog/ErrorLogWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Inspector/BuiltinSmartFeedInspectorViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Inspector/FeedInspectorViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Inspector/FolderInspectorViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Inspector/InspectorWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Inspector/NothingInspectorViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/LogTextStyle.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/AddFeed/AddFeedController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/AddFeed/AddFeedWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/AddFeed/FolderTreeMenu.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/AddFolder/AddFolderWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/ArticleExtractorButton.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/ColumnLayoutSplitView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailContainerView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailIconSchemeHandler.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailStatusBarView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailWebView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailWebViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/DetailWindowState.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Detail/Keyboard/DetailKeyboardDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/IconView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Keyboard/MainWindowKeyboardHandler.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/MainWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/MainWindowState.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/NNW3/NNW3Document.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/NNW3/NNW3ImportController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/NNW3/NNW3OpenPanelAccessoryViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/OPML/ExportOPMLWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/OPML/ImportOPMLWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/SharingServiceDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/SharingServicePickerDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCell.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCellAppearance.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/Cell/SidebarCellLayout.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/Keyboard/SidebarKeyboardDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/PasteboardFeed.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/PasteboardFolder.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/Renaming/RenameWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarDeleteItemsAlert.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarOutlineDataSource.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarOutlineView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarStatusBarView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarViewController+ContextualMenus.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/SidebarWindowState.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Sidebar/UnreadCountView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/ArticlePasteboardWriter.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellAppearance.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellData.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/TimelineCellLayout.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/TimelineColumnCellViews.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/TimelineTableCellView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Cell/UnreadIndicatorView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/Keyboard/TimelineKeyboardDelegate.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineColumn.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineContainerView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineContainerViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineLayout.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineTableRowView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineTableView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineViewController+ColumnLayout.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineViewController+ContextualMenus.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/MainWindow/Timeline/TimelineWindowState.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountCell.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsAddCloudKitWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsAddLocalWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsDetailView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsDetailViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsFeedbinWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsNewsBlurWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsPreferencesViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AccountsReaderAPIWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AddAccountHelpView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Accounts/AddAccountsView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/Advanced/AdvancedPreferencesViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/General/GeneralPrefencesViewController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/PreferencesControlsBackgroundView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/PreferencesTableViewBackgroundView.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Preferences/PreferencesWindowController.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/SafariExtension/SafariExtensionHandler.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:314-314` |
| `Mac/SafariExtension/SafariExtensionHandler.swift` | `Subscribe to Feed` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:325-325` |
| `Mac/Scripting/Account+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/AppDelegate+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/Article+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/Author+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/Feed+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/Folder+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/MainWindowController+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/NSApplication+Scriptability.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/NSScriptCommand+NetNewsWire.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/ScriptingObject.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/Scripting/ScriptingObjectContainer.swift` | `NetNewsWire` | folder-synced root Mac | — | `NetNewsWire.xcodeproj/project.pbxproj:805-805` |
| `Mac/ShareExtension/ShareViewController.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:318-318` |
| `Mac/ShareExtension/ShareViewController.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:336-336` |
| `Shared/AccountStats/AccountStatsViewModel.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/AccountStats/AccountStatsViewModel.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/AccountType+Helpers.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/AccountType+Helpers.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Activity/ActivityManager.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Activity/ActivityManager.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Activity/ActivityType.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Activity/ActivityType.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ActivityLog/ActivityLogViewModel.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ActivityLog/ActivityLogViewModel.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/AppDelegate+Shared.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/AppDelegate+Shared.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/AppNotifications.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/AppNotifications.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Extractor/ArticleExtractor.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Extractor/ArticleExtractor.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Extractor/ExtractedArticle.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Extractor/ExtractedArticle.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Rendering/ArticleRenderer.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Rendering/ArticleRenderer.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Rendering/ArticleRenderingSpecialCases.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Rendering/ArticleRenderingSpecialCases.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Rendering/ArticleTextSize.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Rendering/ArticleTextSize.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:441-441` |
| `Shared/Article Rendering/ArticleTextSize.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Article Rendering/WebViewConfiguration.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Article Rendering/WebViewConfiguration.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleSpecifier.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleSpecifier.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:416-416` |
| `Shared/ArticleSpecifier.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleStyles/ArticleTheme+Notifications.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleStyles/ArticleTheme+Notifications.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleStyles/ArticleTheme.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleStyles/ArticleTheme.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleStyles/ArticleThemeDownloader.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleStyles/ArticleThemeDownloader.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleStyles/ArticleThemePlist.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleStyles/ArticleThemePlist.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ArticleStyles/ArticleThemesManager.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ArticleStyles/ArticleThemesManager.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Assets.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Assets.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:417-417` |
| `Shared/Assets.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Commands/DeleteCommand.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Commands/DeleteCommand.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Commands/MarkCommandValidationStatus.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Commands/MarkCommandValidationStatus.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:403-403` |
| `Shared/Commands/MarkStatusCommand.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Commands/MarkStatusCommand.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/CurrentActivity/CurrentActivityViewModel.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/CurrentActivity/CurrentActivityViewModel.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Dinosaurs/DinosaursViewModel.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Dinosaurs/DinosaursViewModel.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Exporters/OPMLExporter.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Exporters/OPMLExporter.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ExtensionPoints/SendToMarsEditCommand.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ExtensionPoints/SendToMarsEditCommand.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:404-404` |
| `Shared/ExtensionPoints/SendToMicroBlogCommand.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ExtensionPoints/SendToMicroBlogCommand.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:405-405` |
| `Shared/Extensions/AddFeedDefaultContainer.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/AddFeedDefaultContainer.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/ArticleStringFormatter.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/ArticleStringFormatter.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/ArticleUtilities.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/ArticleUtilities.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/CacheCleaner.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/CacheCleaner.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/IconImageView.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/IconImageView.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/NSAttributedString+Extensions.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/NSAttributedString+Extensions.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/Node+Extensions.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/Node+Extensions.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:418-418` |
| `Shared/Extensions/Node+Extensions.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/RSImage+Extensions.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/RSImage+Extensions.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Extensions/SmallIconProvider.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Extensions/SmallIconProvider.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/HelpURL.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/HelpURL.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/IconImageCache.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/IconImageCache.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Importers/DefaultFeedsImporter.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Importers/DefaultFeedsImporter.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Settings/AddCloudKitAccount.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Settings/AddCloudKitAccount.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ShareExtension/ExtensionContainers.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ShareExtension/ExtensionContainers.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:442-442` |
| `Shared/ShareExtension/ExtensionContainers.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:419-419` |
| `Shared/ShareExtension/ExtensionContainers.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ShareExtension/ExtensionContainersFile.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ShareExtension/ExtensionContainersFile.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:443-443` |
| `Shared/ShareExtension/ExtensionContainersFile.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:420-420` |
| `Shared/ShareExtension/ExtensionContainersFile.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:444-444` |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:421-421` |
| `Shared/ShareExtension/ExtensionFeedAddRequest.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:445-445` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:422-422` |
| `Shared/ShareExtension/ExtensionFeedAddRequestFile.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/ShareExtension/ShareDefaultContainer.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:392-392` |
| `Shared/ShareExtension/ShareDefaultContainer.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:447-447` |
| `Shared/ShareExtension/ShareDefaultContainer.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:424-424` |
| `Shared/ShareExtension/ShareDefaultContainer.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:407-407` |
| `Shared/SmartFeeds/PseudoFeed.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/PseudoFeed.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SearchFeedDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SearchTimelineFeedDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/SmartFeed.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SmartFeed.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SmartFeedDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/SmartFeedPasteboardWriter.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SmartFeedPasteboardWriter.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:408-408` |
| `Shared/SmartFeeds/SmartFeedsController.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/SmartFeedsController.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/StarredFeedDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/TodayFeedDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/SmartFeeds/UnreadFeed.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/SmartFeeds/UnreadFeed.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timeline/ArticleArray.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timeline/ArticleArray.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timeline/ArticleSortParameters.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timeline/ArticleSortParameters.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timeline/ArticleSorter.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timeline/ArticleSorter.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timeline/FetchRequestOperation.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timeline/FetchRequestOperation.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timeline/FetchRequestQueue.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timeline/FetchRequestQueue.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timer/AccountRefreshTimer.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timer/AccountRefreshTimer.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:409-409` |
| `Shared/Timer/ArticleStatusSyncTimer.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timer/ArticleStatusSyncTimer.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Timer/RefreshInterval.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Timer/RefreshInterval.swift` | `NetNewsWire Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:448-448` |
| `Shared/Timer/RefreshInterval.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Tree/FolderTreeControllerDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Tree/FolderTreeControllerDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Tree/SidebarTreeControllerDelegate.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/Tree/SidebarTreeControllerDelegate.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/UserInfoKey.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/UserInfoKey.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:425-425` |
| `Shared/UserInfoKey.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/UserNotifications/UserNotificationManager.swift` | `NetNewsWire` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:806-806` |
| `Shared/UserNotifications/UserNotificationManager.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Widget/WidgetData.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:393-393` |
| `Shared/Widget/WidgetData.swift` | `NetNewsWire iOS Widget Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:432-432` |
| `Shared/Widget/WidgetData.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Widget/WidgetDataDecoder.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:394-394` |
| `Shared/Widget/WidgetDataDecoder.swift` | `NetNewsWire iOS Widget Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:433-433` |
| `Shared/Widget/WidgetDataDecoder.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Widget/WidgetDataEncoder.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:395-395` |
| `Shared/Widget/WidgetDataEncoder.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Shared/Widget/WidgetDeepLinks.swift` | `NetNewsWire` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:396-396` |
| `Shared/Widget/WidgetDeepLinks.swift` | `NetNewsWire iOS Widget Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:434-434` |
| `Shared/Widget/WidgetDeepLinks.swift` | `NetNewsWire-iOS` | folder-synced root Shared | — | `NetNewsWire.xcodeproj/project.pbxproj:761-761` |
| `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift` | `NetNewsWire-iOSTests` | classic Sources build phase | — | `NetNewsWire.xcodeproj/project.pbxproj:1167-1167` |
| `Tests/NetNewsWire-iOSTests/ActivityItemSourceTests.swift` | `NetNewsWireTests` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:350-350` |
| `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift` | `NetNewsWire-iOSTests` | classic Sources build phase | — | `NetNewsWire.xcodeproj/project.pbxproj:1168-1168` |
| `Tests/NetNewsWire-iOSTests/MultilineUILabelSizerTests.swift` | `NetNewsWireTests` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:351-351` |
| `Tests/NetNewsWireTests/ArticleRenderingSpecialCasesTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ArticleSorterTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ArticleStringFormatterPerformanceTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ArticleStringFormatterTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ExtractBodyFragmentTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLPerformanceTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/NSAttributedStringHTMLTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/SanitizedTitlePerformanceTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/SanitizedTitleTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ScriptingTests/AppleScriptXCTestCase.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ScriptingTests/NSAppleEventDescriptor+UserRecordFields.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ScriptingTests/ScriptingTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/SharingTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Tests/NetNewsWireTests/ThemeUnzipTests.swift` | `NetNewsWireTests` | folder-synced root Tests | — | `NetNewsWire.xcodeproj/project.pbxproj:849-849` |
| `Widget/Shared Views/ArticleItemView.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Shared Views/SizeCategories.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/TimelineProvider.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Widget Views/LockScreenSummaryWidget.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Widget Views/StarredWidget.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Widget Views/TodayWidget.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Widget Views/UnreadWidget.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/Widget Views/WidgetLayout.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `Widget/WidgetBundle.swift` | `NetNewsWire iOS Widget Extension` | folder-synced root Widget | — | `NetNewsWire.xcodeproj/project.pbxproj:650-650` |
| `iOS/Account/AccountIconHeader.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Account/AccountNotificationInspectorView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Account/AccountSheetFooter.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Account/CloudKitAccountView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Account/CredentialsAccountView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Account/LocalAccountView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/AccountStats/AccountStatsView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Add/AddFeedContainerPickerView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Add/AddFeedView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Add/AddFolderView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/AppDefaults.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:378-378` |
| `iOS/AppDefaults.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/AppDelegate.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/AppIntents/AddFeedAppIntent.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/AppIntents/NetNewsWireAppShortcuts.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ArticleExtractorButton.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ArticleIconSchemeHandler.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ArticleSearchBar.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ArticleViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ContextMenuPreviewViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/FindInArticleActivity.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ImageScrollView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ImageTransition.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/ImageViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/OpenInSafariActivity.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/PreloadedWebView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/WebViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/WebViewFullscreenKeeper.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/WebViewProvider.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Article/WrapperScriptMessageHandler.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/ArticleActivityItemSource.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/CurrentActivity/CurrentActivityView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/ErrorHandler.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/HidingReadArticlesState.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/IconView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Inspector/AccountInspectorViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Inspector/FeedInspectorViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Inspector/InspectorIconHeaderView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/KeyboardManager.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionHeaderReusableView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/Collection View Cells/MainFeedCollectionViewFolderCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/Collection View Cells/MainFeedRowIdentifier.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drag.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/MainFeedCollectionViewController+Drop.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/MainFeedCollectionViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainFeed/RefreshProgressView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/MainTimelineCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/MainTimelineCellData.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/MainTimelineCellLayout.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/MultilineUILabelSizer.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/SingleLineUILabelSizer.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/Cell/StringSize+Extensions.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/MainTimelineDataSource.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/MainTimelineModernViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/MainTimeline/MarkAsReadAlertController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/RootSplitViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/SceneCoordinator.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/SceneDelegate.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/AboutContributor.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/AboutCreditView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/AboutView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/ActivityLogView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/AddAccountView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/ArticleThemeImporter.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/ArticleThemesTableViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/CloudKitStatsView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/ColorPaletteTableViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/DinosaurRowView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/DinosaursView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/ErrorLogView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/SettingsComboTableViewCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/SettingsViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/TickMarkSlider.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/TimelineCustomizerCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/TimelineCustomizerCollectionViewController.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/Settings/TimelineHeaderView.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/ShareExtension/ShareFolderPickerCell.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:381-381` |
| `iOS/ShareExtension/ShareFolderPickerCell.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:368-368` |
| `iOS/ShareExtension/ShareFolderPickerController.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:382-382` |
| `iOS/ShareExtension/ShareFolderPickerController.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:369-369` |
| `iOS/ShareExtension/ShareViewController.swift` | `NetNewsWire iOS Share Extension` | added by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:384-384` |
| `iOS/ShareExtension/ShareViewController.swift` | `NetNewsWire-iOS` | excluded by an exception set | — | `NetNewsWire.xcodeproj/project.pbxproj:371-371` |
| `iOS/TitleActivityItemSource.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/UIKit Extensions/UIActivityViewController+Extras.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/UIKit Extensions/UIViewController+Extras.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/UIKit Extensions/VibrantButton.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/UIKit Extensions/VibrantLabel.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |
| `iOS/UIKit Extensions/VibrantTableViewCell.swift` | `NetNewsWire-iOS` | folder-synced root iOS | — | `NetNewsWire.xcodeproj/project.pbxproj:760-760` |

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
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 136-136 — location body; effect enclosing func fetchArticlesMatching
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 646-646 — location body; effect enclosing func fetchArticles
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift` lines 655-655 — location body; effect enclosing func fetchArticlesCount
- `parse-error` `Modules/ArticlesDatabase/Sources/ArticlesDatabase/StatusesTable.swift` lines 179-179 — location body; effect enclosing func fetchArticleIDs
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
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 29-29 — location body; effect enclosing func testOperationAndDependency
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 55-55 — location body; effect enclosing func testOperationAndDependencyAddedOutOfOrder
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 80-80 — location body; effect enclosing func testOperationAndTwoDependenciesAddedOutOfOrder
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 115-115 — location body; effect enclosing func testChildOperationWithTwoDependencies
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 152-152 — location body; effect enclosing func testAddingManyOperations
- `parse-error` `Modules/RSCore/Tests/RSCoreTests/MainThreadOperationTests.swift` lines 190-190 — location body; effect enclosing func testAddingManyOperationsWithCompletionBlocks
- `unresolved-reference` `Modules/RSParser/Package.swift` lines 20-20 — product Tidemark of target RSParser resolves to 0 containers; no edge is drawn
- `parse-error` `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift` lines 70-70 — location declaration header; effect enclosing var feedURL
- `parse-error` `Modules/RSParser/Sources/RSParser/Feeds/JSON/JSONFeedParser.swift` lines 75-75 — location body; effect enclosing func parse
- `parse-error` `Modules/RSParser/Tests/RSParserTests/Feeds/XML/OPMLTests.swift` lines 43-69 — location member; effect enclosing struct OPMLTests
- `parse-error` `Modules/RSParser/Tests/RSParserTests/Utilities/DateParserTests.swift` lines 37-313 — location member; effect enclosing struct DateParserTests
- `parse-error` `Modules/RSParser/Tests/RSParserTests/XML/XMLEncodingTests.swift` lines 32-46 — location member; effect enclosing struct XMLEncodingTests
- `parse-error` `Modules/RSWeb/Sources/RSWeb/DownloadSession.swift` lines 517-517 — location body; effect enclosing var lastOpenRSSOrgFeedRefresh
- `parse-error` `Shared/AccountType+Helpers.swift` lines 22-22 — location member; effect enclosing extension AccountType
- `parse-error` `Shared/Assets.swift` lines 165-165 — location member; effect enclosing struct Colors
- `parse-error` `Shared/HelpURL.swift` lines 22-22 — location member; effect enclosing enum HelpURL
- `parse-error` `Shared/HelpURL.swift` lines 26-26 — location member; effect enclosing enum HelpURL
- `parse-error` `iOS/Article/WebViewController.swift` lines 580-580 — location body; effect enclosing func scrollPositionDidChange
- `parse-error` `iOS/KeyboardManager.swift` lines 110-110 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 114-114 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 118-118 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/KeyboardManager.swift` lines 122-122 — location body; effect enclosing func createKeyModifierFlags
- `parse-error` `iOS/SceneCoordinator.swift` lines 1530-1530 — location body; effect enclosing func showFeedInspector
- `xcconfig-include` `xcconfig/NetNewsWireTests_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_iOSTests_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_ios_target_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_iOSTests_target.xcconfig` lines 2-2 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `path-escape` `xcconfig/NetNewsWire_iOSapp_target.xcconfig` lines 1-1 — #include?
- `xcconfig-include` `xcconfig/NetNewsWire_iOSapp_target.xcconfig` lines 2-2 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_iOSapp_target.xcconfig` lines 3-3 — #include 'xcconfig/common/NetNewsWire_ios_target_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_iOSshareextension_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_iOSextension_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_iOSwidgetextension_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_iOSextension_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_macapp_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_macapp_target.xcconfig` lines 2-2 — #include 'xcconfig/common/NetNewsWire_macapp_target_common.xcconfig'
- `path-escape` `xcconfig/NetNewsWire_project.xcconfig` lines 1-1 — #include?
- `xcconfig-include` `xcconfig/NetNewsWire_project_debug.xcconfig` lines 1-1 — #include 'xcconfig/NetNewsWire_project.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_project_debug.xcconfig` lines 2-2 — #include 'xcconfig/common/NetNewsWire_debug_identifiers.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_project_release.xcconfig` lines 1-1 — #include 'xcconfig/NetNewsWire_project.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_project_release.xcconfig` lines 2-2 — #include 'xcconfig/common/NetNewsWire_release_identifiers.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_safariextension_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_macextension_common.xcconfig'
- `xcconfig-include` `xcconfig/NetNewsWire_shareextension_target.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_macextension_common.xcconfig'
- `conditional-setting` `xcconfig/common/NetNewsWire_codesigning_common.xcconfig` lines 3-3 — CODE_SIGN_IDENTITY[sdk=macosx*]
- `conditional-setting` `xcconfig/common/NetNewsWire_codesigning_common.xcconfig` lines 4-4 — CODE_SIGN_IDENTITY[sdk=iphoneos*]
- `conditional-setting` `xcconfig/common/NetNewsWire_codesigning_common.xcconfig` lines 5-5 — CODE_SIGN_IDENTITY[sdk=iphonesimulator*]
- `path-escape` `xcconfig/common/NetNewsWire_codesigning_common.xcconfig` lines 39-39 — #include?
- `path-escape` `xcconfig/common/NetNewsWire_iOSextension_common.xcconfig` lines 3-3 — #include?
- `xcconfig-include` `xcconfig/common/NetNewsWire_iOSextension_common.xcconfig` lines 4-4 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_iOSextension_common.xcconfig` lines 5-5 — #include 'xcconfig/common/NetNewsWire_ios_target_common.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_ios_target_common.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_version.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_mac_target_common.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_version.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_macapp_target_common.xcconfig` lines 1-1 — #include 'xcconfig/common/NetNewsWire_mac_target_common.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_macextension_common.xcconfig` lines 3-3 — #include 'xcconfig/common/NetNewsWire_codesigning_common.xcconfig'
- `xcconfig-include` `xcconfig/common/NetNewsWire_macextension_common.xcconfig` lines 4-4 — #include 'xcconfig/common/NetNewsWire_mac_target_common.xcconfig'
