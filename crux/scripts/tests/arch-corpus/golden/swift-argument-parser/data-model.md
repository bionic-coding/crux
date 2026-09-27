# Data model

_747 Swift model types (struct, enum, class, actor) with their stored properties and declared relationships, read through the pinned Swift grammar; nothing was compiled or executed._

## Types

| type | kind | access | declared at | conditional |
|---|---|---|---|---|
| `Color` | struct | internal | `Examples/color/Color.swift:14-15` | — |
| `ColorOptions` | enum | public | `Examples/color/Color.swift:31-31` | — |
| `CountLines` | struct | internal | `Examples/count-lines/CountLines.swift:15-17` | — |
| `DefaultAsFlag` | struct | internal | `Examples/default-as-flag/DefaultAsFlag.swift:14-15` | — |
| `Math` | struct | internal | `Examples/math/Math.swift:14-15` | — |
| `Options` | struct | internal | `Examples/math/Math.swift:36-36` | — |
| `Math.Add` | struct | internal | `Examples/math/Math.swift:54-54` | — |
| `Math.Multiply` | struct | internal | `Examples/math/Math.swift:68-68` | — |
| `Math.Statistics` | struct | internal | `Examples/math/Math.swift:84-84` | — |
| `Math.Statistics.Average` | struct | internal | `Examples/math/Math.swift:95-95` | — |
| `Math.Statistics.Average.Kind` | enum | internal | `Examples/math/Math.swift:101-101` | — |
| `Math.Statistics.StandardDeviation` | struct | internal | `Examples/math/Math.swift:167-167` | — |
| `Math.Statistics.Quantiles` | struct | internal | `Examples/math/Math.swift:192-192` | — |
| `Repeat` | struct | internal | `Examples/repeat/Repeat.swift:14-15` | — |
| `SplitMix64` | struct | internal | `Examples/roll/SplitMix64.swift:12-12` | — |
| `RollOptions` | struct | internal | `Examples/roll/main.swift:14-14` | — |
| `GeneratePluginError` | enum | internal | `Plugins/GenerateCommon/GeneratePluginError.swift:15-15` | — |
| `GenerateDoccReferencePlugin` | struct | internal | `Plugins/GenerateDoccReference/GenerateDoccReference.swift:15-16` | — |
| `GenerateManualPlugin` | struct | internal | `Plugins/GenerateManual/GenerateManualPlugin.swift:15-16` | — |
| `CompletionShell` | struct | public | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:15-15` | — |
| `CompletionsGenerator` | struct | internal | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:98-98` | — |
| `Argument` | struct | public | `Sources/ArgumentParser/Parsable Properties/Argument.swift:44-45` | — |
| `ArgumentArrayParsingStrategy` | struct | public | `Sources/ArgumentParser/Parsable Properties/Argument.swift:110-110` | — |
| `ArgumentDiscussion` | enum | internal | `Sources/ArgumentParser/Parsable Properties/ArgumentDiscussion.swift:103-103` | — |
| `ArgumentHelp` | struct | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:13-13` | — |
| `ArgumentVisibility` | struct | public | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:13-13` | — |
| `ArgumentVisibility.Representation` | enum | internal | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:16-16` | — |
| `CompletionKind` | struct | public | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:36-36` | — |
| `CompletionKind.Kind` | enum | internal | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:37-37` | — |
| `ValidationError` | struct | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:14-14` | — |
| `ExitCode` | struct | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:35-35` | — |
| `CleanExit` | struct | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:70-70` | — |
| `CleanExit.Representation` | enum | internal | `Sources/ArgumentParser/Parsable Properties/Errors.swift:71-71` | — |
| `Flag` | struct | public | `Sources/ArgumentParser/Parsable Properties/Flag.swift:71-72` | — |
| `FlagInversion` | struct | public | `Sources/ArgumentParser/Parsable Properties/Flag.swift:135-135` | — |
| `FlagInversion.Representation` | enum | internal | `Sources/ArgumentParser/Parsable Properties/Flag.swift:136-136` | — |
| `FlagExclusivity` | struct | public | `Sources/ArgumentParser/Parsable Properties/Flag.swift:172-172` | — |
| `FlagExclusivity.Representation` | enum | internal | `Sources/ArgumentParser/Parsable Properties/Flag.swift:173-173` | — |
| `NameSpecification` | struct | public | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:33-33` | — |
| `NameSpecification.Element` | struct | public | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:35-35` | — |
| `NameSpecification.Element.Representation` | enum | internal | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:36-36` | — |
| `Option` | struct | public | `Sources/ArgumentParser/Parsable Properties/Option.swift:51-52` | — |
| `SingleValueParsingStrategy` | struct | public | `Sources/ArgumentParser/Parsable Properties/Option.swift:116-116` | — |
| `DefaultAsFlagParsingStrategy` | struct | public | `Sources/ArgumentParser/Parsable Properties/Option.swift:168-168` | — |
| `ArrayParsingStrategy` | struct | public | `Sources/ArgumentParser/Parsable Properties/Option.swift:207-207` | — |
| `OptionGroup` | struct | public | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:33-34` | — |
| `ParentCommand` | struct | public | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:42-43` | — |
| `CommandConfiguration` | struct | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:13-13` | — |
| `CommandGroup` | struct | public | `Sources/ArgumentParser/Parsable Types/CommandGroup.swift:13-13` | — |
| `_WrappedParsableCommand` | struct | internal | `Sources/ArgumentParser/Parsable Types/ParsableArguments.swift:40-40` | — |
| `DecodedArguments` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:17-17` | — |
| `ArgumentDecoder` | class | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:31-31` | — |
| `ArgumentDecoder.Error` | enum | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:72-72` | — |
| `ParsedArgumentsContainer` | class | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:80-80` | — |
| `SingleValueDecoder` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:173-173` | — |
| `SingleValueDecoder.SingleValueContainer` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:224-224` | — |
| `SingleValueDecoder.UnkeyedContainer` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:250-250` | — |
| `ArrayWrapper` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:304-304` | — |
| `ArgumentDefinition` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:12-12` | — |
| `ArgumentDefinition.Update` | enum | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:15-15` | — |
| `ArgumentDefinition.Kind` | enum | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:33-33` | — |
| `ArgumentDefinition.Help` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:45-45` | — |
| `ArgumentDefinition.Help.Options` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:46-46` | — |
| `ArgumentDefinition.ParsingStrategy` | enum | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:87-87` | — |
| `Bare` | enum | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:381-381` | — |
| `ArgumentSet` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:21-21` | — |
| `LenientParser` | struct | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:255-255` | — |
| `CommandError` | struct | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:12-12` | — |
| `HelpRequested` | struct | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:17-17` | — |
| `CommandParser` | struct | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:21-21` | — |
| `GenerateCompletions` | struct | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:435-435` | — |
| `AutodetectedGenerateCompletions` | struct | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:439-439` | — |
| `InputKey` | struct | internal | `Sources/ArgumentParser/Parsing/InputKey.swift:18-18` | — |
| `InputOrigin` | struct | internal | `Sources/ArgumentParser/Parsing/InputOrigin.swift:30-30` | — |
| `InputOrigin.Element` | enum | internal | `Sources/ArgumentParser/Parsing/InputOrigin.swift:31-31` | — |
| `Name` | enum | internal | `Sources/ArgumentParser/Parsing/Name.swift:12-12` | — |
| `Name.Case` | enum | internal | `Sources/ArgumentParser/Parsing/Name.swift:50-50` | — |
| `Parsed` | enum | internal | `Sources/ArgumentParser/Parsing/Parsed.swift:12-12` | — |
| `ParsedValues` | struct | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:15-15` | — |
| `ParsedValues.Element` | struct | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:16-16` | — |
| `ParserError` | enum | internal | `Sources/ArgumentParser/Parsing/ParserError.swift:13-13` | — |
| `InternalParseError` | enum | internal | `Sources/ArgumentParser/Parsing/ParserError.swift:45-45` | — |
| `ParsedArgument` | enum | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:15-15` | — |
| `SplitArguments` | struct | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:89-89` | — |
| `SplitArguments.Element` | struct | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:90-90` | — |
| `SplitArguments.Element.Value` | enum | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:91-91` | — |
| `SplitArguments.InputIndex` | struct | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:127-127` | — |
| `SplitArguments.SubIndex` | enum | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:144-144` | — |
| `SplitArguments.Index` | struct | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:161-161` | — |
| `DumpHelpGenerator` | struct | internal | `Sources/ArgumentParser/Usage/DumpHelpGenerator.swift:14-14` | — |
| `HelpCommand` | struct | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:12-12` | — |
| `HelpCommand.CodingKeys` | enum | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:51-51` | — |
| `HelpGenerator` | struct | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:12-12` | — |
| `HelpGenerator.Section` | struct | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:17-17` | — |
| `HelpGenerator.Section.Element` | struct | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:18-18` | — |
| `HelpGenerator.Section.Header` | enum | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:108-108` | — |
| `HelpGenerator.DiscussionSection` | struct | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:146-146` | — |
| `MessageInfo` | enum | internal | `Sources/ArgumentParser/Usage/MessageInfo.swift:12-12` | — |
| `UsageGenerator` | struct | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:12-12` | — |
| `ErrorMessageGenerator` | struct | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:174-174` | — |
| `JSONEncoder` | enum | internal | `Sources/ArgumentParser/Utilities/Foundation.swift:36-36` | — |
| `Mutex` | struct | internal | `Sources/ArgumentParser/Utilities/Mutex.swift:27-27` | — |
| `Mutex._Lock` | struct | private | `Sources/ArgumentParser/Utilities/Mutex.swift:29-29` | — |
| `Mutex._Buffer` | class | private | `Sources/ArgumentParser/Utilities/Mutex.swift:96-96` | — |
| `Platform` | enum | internal | `Sources/ArgumentParser/Utilities/Platform.swift:33-33` | — |
| `Platform.Environment` | enum | internal | `Sources/ArgumentParser/Utilities/Platform.swift:38-38` | — |
| `Platform.Environment.Key` | struct | internal | `Sources/ArgumentParser/Utilities/Platform.swift:39-39` | — |
| `Platform.StandardError` | struct | internal | `Sources/ArgumentParser/Utilities/Platform.swift:191-191` | — |
| `Tree` | class | internal | `Sources/ArgumentParser/Utilities/Tree.swift:12-12` | — |
| `Tree.InitializationError` | enum | internal | `Sources/ArgumentParser/Utilities/Tree.swift:108-108` | — |
| `AsyncCompletionsValidator` | struct | internal | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:14-15` | — |
| `AsyncCompletionsValidator.Error` | struct | internal | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:16-16` | — |
| `CodingKeyValidator` | struct | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:13-13` | — |
| `CodingKeyValidator.Validator` | struct | private | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:14-14` | — |
| `CodingKeyValidator.Validator.ValidationResult` | enum | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:17-17` | — |
| `CodingKeyValidator.MissingKeysError` | struct | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:47-47` | — |
| `CodingKeyValidator.InvalidDecoderError` | struct | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:80-80` | — |
| `NonsenseFlagsValidator` | struct | internal | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:13-13` | — |
| `NonsenseFlagsValidator.Error` | struct | internal | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:14-14` | — |
| `ValidatorErrorKind` | enum | internal | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:44-44` | — |
| `ParsableArgumentsValidationError` | struct | internal | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:53-53` | — |
| `PositionalArgumentsValidator` | struct | internal | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:18-18` | — |
| `PositionalArgumentsValidator.Error` | struct | internal | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:19-19` | — |
| `UniqueNamesValidator` | struct | internal | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:14-14` | — |
| `UniqueNamesValidator.Error` | struct | internal | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:15-15` | — |
| `_BundleMarker` | class | private | `Sources/ArgumentParserTestHelpers/TestHelpers+SwiftTesting.swift:17-17` | — |
| `TestExpectation` | class | public | `Sources/ArgumentParserTestHelpers/TestHelpers+SwiftTesting.swift:26-26` | — |
| `ToolInfoHeader` | struct | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:18-18` | — |
| `ToolInfoV0` | struct | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:30-30` | — |
| `CommandInfoV0` | struct | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:44-44` | — |
| `ArgumentInfoV0` | struct | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:115-115` | — |
| `ArgumentInfoV0.NameInfoV0` | struct | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:117-117` | — |
| `ArgumentInfoV0.NameInfoV0.KindV0` | enum | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:119-119` | — |
| `ArgumentInfoV0.KindV0` | enum | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:140-140` | — |
| `ArgumentInfoV0.ParsingStrategyV0` | enum | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:149-149` | — |
| `ArgumentInfoV0.CompletionKindV0` | enum | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:169-169` | — |
| `AsyncCommandEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:15-15` | — |
| `AsyncStatusCheck` | actor | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:17-17` | — |
| `AsyncStatusCheck.Status` | struct | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:18-18` | — |
| `AsyncCommand` | struct | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:39-39` | — |
| `AsyncCommand.SubCommand` | struct | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:48-48` | — |
| `ParsingEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:16-16` | — |
| `ParsingEndToEndTests.Basics` | struct | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:17-17` | — |
| `ParsingEndToEndTests.Defaults` | struct | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:18-18` | — |
| `ParsingEndToEndTests.Arrays` | struct | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:19-19` | — |
| `Name` | struct | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:22-22` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:41-41` | — |
| `Foo.Subgroup` | enum | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:42-42` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:100-100` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:148-148` | — |
| `DefaultAsFlagEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:16-16` | — |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformExplicitNil` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:21-21` | — |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformNoExplicitNil` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:29-29` | — |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformExplicitNil` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:37-37` | — |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformNoExplicitNil` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:47-47` | — |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagAndArguments` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:150-150` | — |
| `DefaultSubcommandEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:18-18` | — |
| `Main` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:22-22` | — |
| `Default` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:29-29` | — |
| `Default.Mode` | enum | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:30-30` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:37-37` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:38-38` | — |
| `DefaultSubcommandEndToEndTests.MyCommand` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:78-78` | — |
| `DefaultSubcommandEndToEndTests.CommonOptions` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:92-92` | — |
| `DefaultSubcommandEndToEndTests.Plugin` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:99-99` | — |
| `DefaultSubcommandEndToEndTests.NonDefault` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:107-107` | — |
| `DefaultSubcommandEndToEndTests.Other` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:115-115` | — |
| `DefaultSubcommandEndToEndTests.Child` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:119-119` | — |
| `DefaultSubcommandEndToEndTests.BadParent` | struct | fileprivate | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:123-123` | — |
| `DefaultSubcommandEndToEndTests.RootWithPassthroughDefault` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:312-312` | — |
| `DefaultSubcommandEndToEndTests.PassthroughDefault` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:320-320` | — |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:340-340` | — |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.Default` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:346-346` | — |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.Nested` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:348-348` | — |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.NestedDefault` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:356-356` | — |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.NestedOther` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:357-357` | — |
| `DefaultsEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:20-20` | — |
| `Foo.Name` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:21-21` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:57-57` | — |
| `Bar.Format` | enum | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:59-59` | — |
| `Bar_NextInput` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:240-240` | — |
| `Bar_NextInput.Format` | enum | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:241-241` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:300-300` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:404-404` | — |
| `OptionPropertyInitArguments_Default` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:446-446` | — |
| `OptionPropertyInitArguments_NoDefault_NoTransform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:454-454` | — |
| `OptionPropertyInitArguments_NoDefault_Transform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:461-461` | — |
| `ArgumentPropertyInitArguments_Default_NoTransform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:546-546` | — |
| `ArgumentPropertyInitArguments_NoDefault_NoTransform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:553-553` | — |
| `ArgumentPropertyInitArguments_Default_Transform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:560-560` | — |
| `ArgumentPropertyInitArguments_NoDefault_Transform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:567-567` | — |
| `Quux` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:653-653` | — |
| `FlagPropertyInitArguments_Bool_Default` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:683-683` | — |
| `FlagPropertyInitArguments_Bool_NoDefault` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:688-688` | — |
| `HasData` | enum | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:726-726` | — |
| `FlagPropertyInitArguments_EnumerableFlag_Default` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:731-731` | — |
| `FlagPropertyInitArguments_EnumerableFlag_NoDefault` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:738-738` | — |
| `Main` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:785-785` | — |
| `Main.Options` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:791-791` | — |
| `Main.Sub` | struct | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:796-796` | — |
| `RequiredArray_Option_NoTransform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:830-830` | — |
| `RequiredArray_Option_Transform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:835-835` | — |
| `RequiredArray_Argument_NoTransform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:840-840` | — |
| `RequiredArray_Argument_Transform` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:845-845` | — |
| `RequiredArray_Flag` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:850-850` | — |
| `OptionPropertyDeprecatedInit_NoDefault` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:981-982` | — |
| `DefaultsEndToEndTests.AbsolutePath` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1001-1001` | — |
| `DefaultsEndToEndTests.TwoPaths` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1006-1006` | — |
| `DefaultsEndToEndTests.UnderscoredOptional` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1036-1036` | — |
| `DefaultsEndToEndTests.UnderscoredArray` | struct | private | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1041-1041` | — |
| `EnumEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:20-20` | — |
| `Bar.Index` | enum | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:21-21` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:57-57` | — |
| `Baz.Mode` | enum | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:58-58` | — |
| `EqualsEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:20-20` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:51-51` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:68-68` | — |
| `LongOptionWithFile` | struct | private | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:85-85` | — |
| `LongOptionWithOptionalString` | struct | private | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:90-90` | — |
| `FlagsEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:20-20` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:96-96` | — |
| `Color` | enum | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:155-155` | — |
| `Size` | enum | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:161-161` | — |
| `Shape` | enum | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:193-193` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:199-199` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:320-320` | — |
| `RepeatOK` | struct | private | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:362-362` | — |
| `JoinedEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:20-20` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:100-100` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:133-133` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:175-175` | — |
| `LongNameWithSingleDashEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:20-20` | — |
| `LongNameWithSingleDashEndToEndTests.Issue327` | struct | private | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:112-112` | — |
| `LongNameWithSingleDashEndToEndTests.JoinedItem` | struct | private | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:127-127` | — |
| `NestedCommandEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:20-20` | — |
| `Foo.Build` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:27-27` | — |
| `Foo.Package` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:34-34` | — |
| `Foo.Package.Clean` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:43-43` | — |
| `Foo.Package.Config` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:48-48` | — |
| `Options` | struct | private | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:281-281` | — |
| `UniqueOptions` | struct | private | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:285-285` | — |
| `Super` | struct | private | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:289-289` | — |
| `Super.Sub1` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:296-296` | — |
| `Super.Sub2` | struct | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:300-300` | — |
| `OptionGroupEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:16-16` | — |
| `ValidationConfirmations` | enum | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:18-18` | — |
| `Inner` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:24-24` | — |
| `Outer` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:37-37` | — |
| `Command` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:52-52` | — |
| `DuplicatedFlagGroupCustom` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:129-129` | — |
| `DuplicatedFlagGroupCustomCommand` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:134-134` | — |
| `DuplicatedFlagGroupLong` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:139-139` | — |
| `DuplicatedFlagGroupLongCommand` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:143-143` | — |
| `OptionalEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:20-20` | — |
| `Foo.Name` | struct | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:21-21` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:57-57` | — |
| `Bar.Format` | enum | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:59-59` | — |
| `OptionalEndToEndTests.Command` | struct | private | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:232-232` | — |
| `OptionalEndToEndTests.Command.MyError` | struct | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:233-233` | — |
| `OptionalEndToEndTests.Command.Foo` | struct | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:234-234` | — |
| `PositionalEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:20-20` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:56-56` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:104-104` | — |
| `Wobble` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:148-148` | — |
| `Flob` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:203-203` | — |
| `BadlyFormed` | struct | private | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:239-239` | — |
| `PositionalEndToEndTests.HasRange` | struct | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:271-271` | — |
| `RawRepresentableEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:20-20` | — |
| `Bar.Identifier` | struct | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:21-21` | — |
| `LogLevel` | struct | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:55-55` | — |
| `AllUnrecognizedArgs` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:19-19` | — |
| `AllUnrecognizedRoot` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:80-80` | — |
| `AllUnrecognizedRoot.Child` | struct | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:87-87` | — |
| `PostTerminatorArgs` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:128-128` | — |
| `PassthroughArgs` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:184-184` | — |
| `RepeatingEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:17-17` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:21-21` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:47-47` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:69-69` | — |
| `Outer` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:139-139` | — |
| `Inner` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:143-143` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:166-166` | — |
| `Wobble` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:274-274` | — |
| `Wobble.WobbleError` | struct | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:275-275` | — |
| `Wobble.Name` | struct | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:276-276` | — |
| `Weazle` | struct | private | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:373-373` | — |
| `PerformanceTest` | struct | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:402-402` | — |
| `ShortNameEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:20-20` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:90-90` | — |
| `SimpleEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:20-20` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:66-66` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:109-109` | — |
| `SingleValueParsingStrategyTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:16-16` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:20-20` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:61-61` | — |
| `SourceCompatEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:18-18` | — |
| `AlmostAllArguments` | struct | private | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:23-23` | — |
| `AllOptions` | struct | private | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:64-64` | — |
| `AllFlags` | struct | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:153-153` | — |
| `AllFlags.E` | enum | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:154-154` | — |
| `SubcommandEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:16-16` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:20-20` | — |
| `CommandA` | struct | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:27-27` | — |
| `CommandB` | struct | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:35-35` | — |
| `Math` | struct | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:128-128` | — |
| `Math.Operation` | enum | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:129-129` | — |
| `BaseCommand` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:167-167` | — |
| `BaseCommand.BaseCommandError` | enum | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:168-168` | — |
| `BaseCommand.SubCommand` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:191-191` | — |
| `BaseCommand.SubCommand.SubSubCommand` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:211-211` | — |
| `BaseCommand.SubCommand.SubSubCommand.CodingKeys` | enum | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:221-221` | — |
| `A` | struct | private | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:268-268` | — |
| `A.HasVersionFlag` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:273-273` | — |
| `A.NoVersionFlag` | struct | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:277-277` | — |
| `TransformEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:16-16` | — |
| `FooBarError` | enum | private | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:18-18` | — |
| `FooOption` | struct | private | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:38-38` | — |
| `BarOption` | struct | private | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:53-53` | — |
| `FooArgument` | struct | private | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:123-123` | — |
| `FooArgument.FooError` | enum | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:131-131` | — |
| `BarArgument` | struct | private | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:141-141` | — |
| `UnparsedValuesEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:16-16` | — |
| `Qux` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:20-20` | — |
| `Quizzo` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:26-26` | — |
| `Hogeraa` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:68-68` | — |
| `Hogera` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:72-72` | — |
| `Piyo` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:81-81` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:148-148` | — |
| `Config` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:155-155` | — |
| `OptionalArguments` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:160-160` | — |
| `DefaultedArguments` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:165-165` | — |
| `Barr` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:201-201` | — |
| `Bar` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:205-205` | — |
| `Baz` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:217-217` | — |
| `Bazz` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:222-222` | — |
| `Bamf` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:318-318` | — |
| `Qiqi` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:337-337` | — |
| `Qiqii` | enum | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:342-342` | — |
| `Fry` | struct | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:364-364` | — |
| `Toks` | class | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:369-369` | — |
| `Vig` | class | private | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:373-373` | — |
| `ValidationEndToEndTests` | struct | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:17-17` | — |
| `UserValidationError` | enum | private | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:19-19` | — |
| `Foo` | struct | private | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:30-30` | — |
| `FooCommand` | struct | private | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:161-161` | — |
| `ValidateCountingArguments` | struct | private | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:186-186` | — |
| `ValidateCountingCommand` | struct | private | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:194-194` | — |
| `CountLinesExampleTests` | struct | internal | `Tests/ArgumentParserExampleTests/CountLinesExampleTests.swift:20-22` | yes |
| `MathExampleTests` | struct | internal | `Tests/ArgumentParserExampleTests/MathExampleTests.swift:17-19` | — |
| `RepeatExampleTests` | struct | internal | `Tests/ArgumentParserExampleTests/RepeatExampleTests.swift:17-19` | — |
| `RollDiceExampleTests` | struct | internal | `Tests/ArgumentParserExampleTests/RollDiceExampleTests.swift:17-19` | — |
| `GenerateDoccReferenceTests` | struct | internal | `Tests/ArgumentParserGenerateDoccReferenceTests/GenerateDoccReferenceTests.swift:15-15` | — |
| `GenerateManualTests` | struct | internal | `Tests/ArgumentParserGenerateManualTests/GenerateManualTests.swift:15-15` | — |
| `HelpTests` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:17-17` | — |
| `Simple` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:170-170` | — |
| `CustomHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:196-196` | — |
| `NoHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:219-219` | — |
| `SubCommandCustomHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:253-253` | — |
| `SubCommandCustomHelp.InheritHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:258-258` | — |
| `SubCommandCustomHelp.ModifiedHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:262-262` | — |
| `SubCommandCustomHelp.ModifiedHelp.InheritImmediateParentdHelp` | struct | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:267-267` | — |
| `Package.Clean` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Clean.swift:15-15` | — |
| `Package.Config` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:16-16` | — |
| `Package.Config.GetMirror` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:24-24` | — |
| `Package.Config.SetMirror` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:34-34` | — |
| `Package.Config.UnsetMirror` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:47-47` | — |
| `Package.Describe` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:16-16` | — |
| `Package.Describe.OutputType` | enum | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:23-23` | — |
| `Package.GenerateXcodeProject` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:16-16` | — |
| `Options` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:14-14` | — |
| `Options.Configuration` | enum | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:18-18` | — |
| `Package` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:107-107` | — |
| `Package.Hidden` | struct | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:116-116` | — |
| `Tests` | struct | internal | `Tests/ArgumentParserPackageManagerTests/Tests.swift:17-17` | — |
| `ArgumentParserToolInfoTests` | struct | internal | `Tests/ArgumentParserToolInfoTests/ArgumentParserToolInfoTests.swift:64-64` | — |
| `SerializedTests.CompletionScriptTests` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:35-35` | — |
| `SerializedTests.CompletionScriptTests.Path` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:40-40` | — |
| `SerializedTests.CompletionScriptTests.Kind` | enum | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:52-52` | — |
| `SerializedTests.CompletionScriptTests.NestedArguments` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:62-62` | — |
| `SerializedTests.CompletionScriptTests.Base` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:67-67` | — |
| `SerializedTests.CompletionScriptTests.Base.SubCommand` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:91-91` | — |
| `SerializedTests.CompletionScriptTests.Base.HiddenChild` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:96-96` | — |
| `SerializedTests.CompletionScriptTests.Base.EscapedCommand` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:100-100` | — |
| `SerializedTests.CompletionScriptTests.Custom` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:159-159` | — |
| `SerializedTests.CompletionScriptTests.Custom.NestedArguments` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:177-177` | — |
| `SerializedTests.CompletionScriptTests.CustomAsync` | struct | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:183-183` | — |
| `SerializedTests.DefaultAsFlagCompletionTests` | struct | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:18-18` | — |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | struct | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:45-45` | — |
| `DefaultAsFlagDumpHelpTests` | struct | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:17-17` | — |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | struct | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:28-28` | — |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | struct | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:46-46` | — |
| `DumpHelpGenerationTests` | struct | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:17-17` | — |
| `DumpHelpGenerationTests.A` | struct | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:56-56` | — |
| `DumpHelpGenerationTests.A.TestEnum` | enum | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:57-57` | — |
| `DumpHelpGenerationTests.Options` | struct | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:88-88` | — |
| `DumpHelpGenerationTests.B` | struct | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:96-96` | — |
| `DumpHelpGenerationTests.C` | struct | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:101-101` | — |
| `DumpHelpGenerationTests.C.Color` | enum | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:104-104` | — |
| `ErrorCase` | struct | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:17-17` | — |
| `ErrorMessageTests` | struct | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:24-24` | — |
| `Bar` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:28-28` | — |
| `Format` | enum | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` | — |
| `Name` | enum | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` | — |
| `Counter` | enum | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:103-103` | — |
| `Foo` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:108-108` | — |
| `EnumWithFewCasesArrayArgument` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:115-115` | — |
| `EnumWithManyCasesArrayArgument` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:120-120` | — |
| `EnumWithIntRawValue` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:125-125` | — |
| `Baz` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:208-208` | — |
| `Qux` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:222-222` | — |
| `Qwz` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:252-252` | — |
| `Options` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:291-291` | — |
| `Options.OutputBehaviour` | enum | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:292-292` | — |
| `OptOptions` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:306-306` | — |
| `OptOptions.OutputBehaviour` | enum | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:307-307` | — |
| `EmptyArray` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:361-361` | — |
| `Repeat` | struct | private | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:401-401` | — |
| `ExitCodeTests` | struct | internal | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:17-17` | — |
| `ExitCodeTests.A` | struct | internal | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:23-23` | — |
| `ExitCodeTests.E` | struct | internal | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:24-24` | — |
| `ExitCodeTests.C` | struct | internal | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:25-25` | — |
| `HelpGenerationTests.AtArgumentTransform` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:22-22` | — |
| `HelpGenerationTests.AtArgumentTransform.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:24-24` | — |
| `HelpGenerationTests.AtArgumentTransform.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:26-26` | — |
| `HelpGenerationTests.AtArgumentTransform.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:31-31` | — |
| `HelpGenerationTests.AtArgumentTransform.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:36-36` | — |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:41-41` | — |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:46-46` | — |
| `HelpGenerationTests.AtArgumentTransform.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:51-51` | — |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:56-56` | — |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:61-61` | — |
| `HelpGenerationTests.AtArgumentEBA` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:198-198` | — |
| `HelpGenerationTests.AtArgumentEBA.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:200-200` | — |
| `HelpGenerationTests.AtArgumentEBA.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:207-207` | — |
| `HelpGenerationTests.AtArgumentEBA.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:212-212` | — |
| `HelpGenerationTests.AtArgumentEBA.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:217-217` | — |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:222-222` | — |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:227-228` | — |
| `HelpGenerationTests.AtArgumentEBA.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:233-233` | — |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:238-238` | — |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:243-243` | — |
| `HelpGenerationTests.AtArgumentEBATransform` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:364-364` | — |
| `HelpGenerationTests.AtArgumentEBATransform.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:366-366` | — |
| `HelpGenerationTests.AtArgumentEBATransform.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:373-373` | — |
| `HelpGenerationTests.AtArgumentEBATransform.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:378-378` | — |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:383-383` | — |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:388-388` | — |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:393-393` | — |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:398-398` | — |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:403-403` | — |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:408-408` | — |
| `HelpGenerationTests.AtOptionTransform` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:22-22` | — |
| `HelpGenerationTests.AtOptionTransform.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:24-24` | — |
| `HelpGenerationTests.AtOptionTransform.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:26-26` | — |
| `HelpGenerationTests.AtOptionTransform.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:31-31` | — |
| `HelpGenerationTests.AtOptionTransform.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:36-36` | — |
| `HelpGenerationTests.AtOptionTransform.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:41-41` | — |
| `HelpGenerationTests.AtOptionTransform.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:46-46` | — |
| `HelpGenerationTests.AtOptionTransform.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:51-51` | — |
| `HelpGenerationTests.AtOptionTransform.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:56-56` | — |
| `HelpGenerationTests.AtOptionTransform.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:61-61` | — |
| `HelpGenerationTests.AtOptionEBA` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:174-174` | — |
| `HelpGenerationTests.AtOptionEBA.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:176-176` | — |
| `HelpGenerationTests.AtOptionEBA.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:183-183` | — |
| `HelpGenerationTests.AtOptionEBA.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:188-188` | — |
| `HelpGenerationTests.AtOptionEBA.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:193-193` | — |
| `HelpGenerationTests.AtOptionEBA.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:198-198` | — |
| `HelpGenerationTests.AtOptionEBA.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:203-204` | — |
| `HelpGenerationTests.AtOptionEBA.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:209-209` | — |
| `HelpGenerationTests.AtOptionEBA.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:214-214` | — |
| `HelpGenerationTests.AtOptionEBA.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:219-219` | — |
| `HelpGenerationTests.AtOptionEBATransform` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:319-319` | — |
| `HelpGenerationTests.AtOptionEBATransform.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:321-321` | — |
| `HelpGenerationTests.AtOptionEBATransform.BareNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:328-328` | — |
| `HelpGenerationTests.AtOptionEBATransform.BareDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:333-333` | — |
| `HelpGenerationTests.AtOptionEBATransform.OptionalNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:338-338` | — |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefaultNil` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:343-343` | — |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:348-348` | — |
| `HelpGenerationTests.AtOptionEBATransform.ArrayNoDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:353-353` | — |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefaultEmpty` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:358-358` | — |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:363-363` | — |
| `HelpGenerationTests.BasicDefaultAsFlag` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:19-19` | — |
| `HelpGenerationTests.DefaultAsFlagWithShortNames` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:64-64` | — |
| `HelpGenerationTests.MixedOptionTypes` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:91-91` | — |
| `HelpGenerationTests.Flags` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:21-21` | — |
| `HelpGenerationTests.Options` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:29-29` | — |
| `HelpGenerationTests.FlagsAndOptions` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:37-37` | — |
| `HelpGenerationTests.ArgsAndFlags` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:45-45` | — |
| `HelpGenerationTests.AllVisible` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:56-56` | — |
| `HelpGenerationTests.ContainsOptionGroup` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:70-70` | — |
| `HelpGenerationTests.Combined` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:129-129` | — |
| `HelpGenerationTests.HiddenGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:190-190` | — |
| `HelpGenerationTests.NestedGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:236-236` | — |
| `HelpGenerationTests.NestedHiddenGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:244-244` | — |
| `HelpGenerationTests.ParentWithGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:273-273` | — |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:284-284` | — |
| `HelpGenerationTests.GroupsWithUnnamedGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:390-390` | — |
| `HelpGenerationTests.GroupsWithNamedGroups` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:415-415` | — |
| `HelpGenerationTests.Root` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:21-21` | — |
| `HelpGenerationTests.Root.Inherits` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:28-28` | — |
| `HelpGenerationTests.Root.Inherits.Nested` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:33-33` | — |
| `HelpGenerationTests.Root.Overrides` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:39-39` | — |
| `HelpGenerationTests.Root.Overrides.Nested` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:45-45` | — |
| `HelpGenerationTests.Root.Suppresses` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:51-51` | — |
| `HelpGenerationTests.NoBanner` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:147-147` | — |
| `HelpGenerationTests.VerbatimBanner` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:167-167` | — |
| `HelpGenerationTests.BannerNoAbstract` | struct | fileprivate | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:198-198` | — |
| `HelpGenerationTests` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:18-20` | — |
| `HelpGenerationTests.A` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:39-39` | — |
| `HelpGenerationTests.B` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:58-58` | — |
| `HelpGenerationTests.C` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:102-102` | — |
| `HelpGenerationTests.Issue27` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:124-124` | — |
| `HelpGenerationTests.OptionFlags` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:151-151` | — |
| `HelpGenerationTests.Degree` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:152-152` | — |
| `HelpGenerationTests.D` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:170-170` | — |
| `HelpGenerationTests.D.Manual` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:197-197` | — |
| `HelpGenerationTests.D.UnspecializedSynthesized` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:204-204` | — |
| `HelpGenerationTests.D.SpecializedSynthesized` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:210-210` | — |
| `HelpGenerationTests.E` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:244-244` | — |
| `HelpGenerationTests.E.OutputBehaviour` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:245-245` | — |
| `HelpGenerationTests.F` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:257-257` | — |
| `HelpGenerationTests.F.OutputBehaviour` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:258-258` | — |
| `HelpGenerationTests.G` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:270-270` | — |
| `HelpGenerationTests.H` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:311-311` | — |
| `HelpGenerationTests.H.CommandWithVeryLongName` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:312-312` | — |
| `HelpGenerationTests.H.ShortCommand` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:313-313` | — |
| `HelpGenerationTests.H.AnotherCommandWithVeryLongName` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:317-317` | — |
| `HelpGenerationTests.H.AnotherCommand` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:321-321` | — |
| `HelpGenerationTests.I` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:381-381` | — |
| `HelpGenerationTests.J` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:399-399` | — |
| `HelpGenerationTests.K` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:420-420` | — |
| `HelpGenerationTests.L` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:446-446` | — |
| `HelpGenerationTests.M` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:471-471` | — |
| `HelpGenerationTests.N` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:473-473` | — |
| `HelpGenerationTests.O` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:494-494` | — |
| `HelpGenerationTests.P` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:506-506` | — |
| `HelpGenerationTests.Foo` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:530-530` | — |
| `HelpGenerationTests.Bar` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:545-545` | — |
| `HelpGenerationTests.WithSubgroups` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:574-574` | — |
| `HelpGenerationTests.OnlySubgroups` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:611-611` | — |
| `HelpGenerationTests.OptionsToHide` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:650-650` | — |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:664-665` | — |
| `HelpGenerationTests.HideOptionGroupDriver` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:676-676` | — |
| `HelpGenerationTests.PrivateOptionGroupDriver` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:687-687` | — |
| `HelpGenerationTests.AllValues` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:752-752` | — |
| `HelpGenerationTests.AllValues.Manual` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:753-753` | — |
| `HelpGenerationTests.AllValues.UnspecializedSynthesized` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:758-758` | — |
| `HelpGenerationTests.AllValues.SpecializedSynthesized` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:762-762` | — |
| `HelpGenerationTests.Q` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:807-807` | — |
| `HelpGenerationTests.ParserBug` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:836-836` | — |
| `HelpGenerationTests.ParserBug.CommonOptions` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:841-841` | — |
| `HelpGenerationTests.ParserBug.Sub` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:846-846` | — |
| `HelpGenerationTests.NonCustomUsage` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:873-873` | — |
| `HelpGenerationTests.NonCustomUsage.ExampleSubcommand` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:874-874` | — |
| `HelpGenerationTests.CustomUsageShort` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:886-886` | — |
| `HelpGenerationTests.CustomUsageLong` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:896-896` | — |
| `HelpGenerationTests.CustomUsageHidden` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:908-908` | — |
| `HelpGenerationTests.OptionValues` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1065-1065` | — |
| `HelpGenerationTests.CustomOption` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1082-1082` | — |
| `HelpGenerationTests.CustomOptionAsListWithSingleDefaultValue` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1102-1102` | — |
| `HelpGenerationTests.CustomOptionAsListWithMultipleDefaultValue` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1126-1126` | — |
| `HelpGenerationTests.CustomOptionAsListWithEmptyArrayAsDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1151-1151` | — |
| `HelpGenerationTests.CustomOptionWithDefault` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1176-1176` | — |
| `HelpGenerationTests.Optional` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1198-1198` | — |
| `HelpGenerationTests.NoAbstract` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1218-1218` | — |
| `HelpGenerationTests.Preamble` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1244-1244` | — |
| `HelpGenerationTests.OptionWithoutEnumerationHelpText` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1290-1290` | — |
| `HelpGenerationTests.HelpTextComparison` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1298-1298` | — |
| `HelpGenerationTests.Empty` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1329-1329` | — |
| `HelpGenerationTests.EmptyCommand` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1339-1339` | — |
| `HelpGenerationTests.Cases` | enum | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1358-1358` | — |
| `HelpGenerationTests.LongLabelHelp` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1380-1380` | — |
| `HelpGenerationTests.LongLabelHelpWithOptionDescription` | struct | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1410-1410` | — |
| `HelpGenerationTests.WideHelp` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1449-1449` | — |
| `HelpGenerationTests.OptionGroupOptions` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1505-1505` | — |
| `HelpGenerationTests.OptionGroupCommand` | struct | private | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1510-1510` | — |
| `InputOriginTests` | struct | internal | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:16-16` | — |
| `InputOriginTests.IsDefaultTestData` | struct | internal | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:20-20` | — |
| `MirrorTests` | struct | internal | `Tests/ArgumentParserUnitTests/MirrorTests.swift:16-16` | — |
| `MirrorTests.Foo` | struct | private | `Tests/ArgumentParserUnitTests/MirrorTests.swift:17-17` | — |
| `NameSpecificationTests` | struct | internal | `Tests/ArgumentParserUnitTests/NameSpecificationTests.swift:16-16` | — |
| `ParsableArgumentsValidationTests` | struct | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:17-17` | — |
| `ParsableArgumentsValidationTests.A` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:18-18` | — |
| `ParsableArgumentsValidationTests.A.CodingKeys` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:25-25` | — |
| `ParsableArgumentsValidationTests.B` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:33-33` | — |
| `ParsableArgumentsValidationTests.C` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:43-43` | — |
| `ParsableArgumentsValidationTests.C.CodingKeys` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:50-50` | — |
| `ParsableArgumentsValidationTests.D` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:57-57` | — |
| `ParsableArgumentsValidationTests.D.CodingKeys` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:64-64` | — |
| `ParsableArgumentsValidationTests.E` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:69-69` | — |
| `ParsableArgumentsValidationTests.E.CodingKeys` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:79-79` | — |
| `ParsableArgumentsValidationTests.TypeWithInvalidDecoder` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:120-120` | — |
| `ParsableArgumentsValidationTests.AsyncCompletionOptionGroup` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:149-150` | — |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:173-174` | — |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:210-211` | — |
| `ParsableArgumentsValidationTests.TypeWithValidSyncCompletions` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:237-238` | — |
| `ParsableArgumentsValidationTests.F` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:262-262` | — |
| `ParsableArgumentsValidationTests.G` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:270-270` | — |
| `ParsableArgumentsValidationTests.H` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:278-278` | — |
| `ParsableArgumentsValidationTests.I` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:286-286` | — |
| `ParsableArgumentsValidationTests.J` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:294-294` | — |
| `ParsableArgumentsValidationTests.J.Options` | struct | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:295-295` | — |
| `ParsableArgumentsValidationTests.K` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:307-307` | — |
| `ParsableArgumentsValidationTests.K.Options` | struct | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:308-308` | — |
| `ParsableArgumentsValidationTests.L` | struct | private | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:321-321` | — |
| `ParsableArgumentsValidationTests.L.Options` | struct | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:322-322` | — |
| `ParsableArgumentsValidationTests.DifferentNames` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:369-369` | — |
| `ParsableArgumentsValidationTests.TwoOfTheSameName` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:385-385` | — |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:407-407` | — |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:447-447` | — |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument.Versimilitude` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:451-451` | — |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:475-475` | — |
| `ParsableArgumentsValidationTests.FourDuplicateNames.Numbers` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:485-485` | — |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:510-510` | — |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames.ExampleEnum` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:511-511` | — |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:527-527` | — |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames.ExampleEnum` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:528-528` | — |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:562-562` | — |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag.ExampleEnum` | enum | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:563-563` | — |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | struct | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:610-610` | — |
| `SendableTests` | struct | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:16-16` | — |
| `SendableTests.MyExpressibleType` | struct | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:18-18` | — |
| `SendableTests.SendableClassType` | class | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:22-22` | — |
| `SendableTests.NonSendableClassType` | class | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:26-26` | — |
| `SendableTests.Foo` | struct | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:36-36` | — |
| `SendableTests.Bar` | struct | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:53-53` | — |
| `SendableTests.Baz` | struct | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:58-58` | — |
| `SequenceExtensionTests` | struct | internal | `Tests/ArgumentParserUnitTests/SequenceExtensionTests.swift:16-16` | — |
| `SerializedCompletionSuites` | enum | internal | `Tests/ArgumentParserUnitTests/SerializedCompletionSuites.swift:23-26` | — |
| `SerializedTests` | struct | internal | `Tests/ArgumentParserUnitTests/SerializedTestSuite.swift:14-16` | — |
| `StringEditDistanceTests` | struct | internal | `Tests/ArgumentParserUnitTests/StringEditDistanceTests.swift:16-16` | — |
| `StringSnakeCaseTests` | struct | internal | `Tests/ArgumentParserUnitTests/StringSnakeCaseTests.swift:16-17` | — |
| `StringWrappingTests` | struct | internal | `Tests/ArgumentParserUnitTests/StringWrappingTests.swift:44-44` | — |
| `TreeTests` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:16-16` | — |
| `TreeTests.A` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:58-58` | — |
| `TreeTests.Root` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:61-61` | — |
| `TreeTests.Sub` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:64-64` | — |
| `TreeTests.RootWithNamedNestedSub` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:68-68` | — |
| `TreeTests.RootWithNamedNestedSub.NestedSub` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:73-73` | — |
| `TreeTests.RootWithNestedSub` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:79-79` | — |
| `TreeTests.RootWithNestedSub.NestedSub` | struct | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:84-84` | — |
| `UsageGenerationTests` | struct | internal | `Tests/ArgumentParserUnitTests/UsageGenerationTests.swift:16-16` | — |
| `ChangelogAuthors` | struct | internal | `Tools/changelog-authors/ChangelogAuthors.swift:19-21` | yes |
| `Comparison` | struct | internal | `Tools/changelog-authors/Models.swift:14-14` | — |
| `Commit` | struct | internal | `Tools/changelog-authors/Models.swift:18-18` | — |
| `Author` | struct | internal | `Tools/changelog-authors/Models.swift:23-23` | — |
| `Author.CodingKeys` | enum | internal | `Tools/changelog-authors/Models.swift:27-27` | — |
| `SubprocessError` | enum | internal | `Tools/generate-docc-reference/Extensions/Process+SimpleAPI.swift:14-14` | — |
| `GenerateDoccReferenceError` | enum | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:16-16` | — |
| `OutputStyle` | enum | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:40-40` | — |
| `GenerateDoccReference` | struct | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:47-48` | — |
| `AuthorArgument` | enum | internal | `Tools/generate-manual/AuthorArgument.swift:35-35` | — |
| `ArgumentSynopsis` | struct | internal | `Tools/generate-manual/DSL/ArgumentSynopsis.swift:15-15` | — |
| `Author` | struct | internal | `Tools/generate-manual/DSL/Author.swift:15-15` | — |
| `Authors` | struct | internal | `Tools/generate-manual/DSL/Authors.swift:15-15` | — |
| `Container` | struct | internal | `Tools/generate-manual/DSL/Core/Container.swift:15-15` | — |
| `Empty` | struct | internal | `Tools/generate-manual/DSL/Core/Empty.swift:12-12` | — |
| `ForEach` | struct | internal | `Tools/generate-manual/DSL/Core/ForEach.swift:12-12` | — |
| `MDocASTNodeWrapper` | struct | internal | `Tools/generate-manual/DSL/Core/MDocASTNodeWrapper.swift:12-12` | — |
| `MDocBuilder` | struct | internal | `Tools/generate-manual/DSL/Core/MDocBuilder.swift:12-13` | — |
| `DiscussionText` | struct | internal | `Tools/generate-manual/DSL/Discussion.swift:14-14` | — |
| `Document` | struct | internal | `Tools/generate-manual/DSL/Document.swift:16-16` | — |
| `DocumentDate` | struct | internal | `Tools/generate-manual/DSL/DocumentDate.swift:16-16` | — |
| `Exit` | struct | internal | `Tools/generate-manual/DSL/Exit.swift:15-15` | — |
| `List` | struct | internal | `Tools/generate-manual/DSL/List.swift:12-12` | — |
| `MultiPageDescription` | struct | internal | `Tools/generate-manual/DSL/MultiPageDescription.swift:15-15` | — |
| `Name` | struct | internal | `Tools/generate-manual/DSL/Name.swift:15-15` | — |
| `Preamble` | struct | internal | `Tools/generate-manual/DSL/Preamble.swift:16-16` | — |
| `Section` | struct | internal | `Tools/generate-manual/DSL/Section.swift:12-12` | — |
| `SeeAlso` | struct | internal | `Tools/generate-manual/DSL/SeeAlso.swift:15-15` | — |
| `SinglePageDescription` | struct | internal | `Tools/generate-manual/DSL/SinglePageDescription.swift:15-15` | — |
| `Synopsis` | struct | internal | `Tools/generate-manual/DSL/Synopsis.swift:15-15` | — |
| `SubprocessError` | enum | internal | `Tools/generate-manual/Extensions/Process+SimpleAPI.swift:14-14` | — |
| `GenerateManualError` | enum | internal | `Tools/generate-manual/GenerateManual.swift:16-16` | — |
| `GenerateManual` | struct | internal | `Tools/generate-manual/GenerateManual.swift:39-40` | — |
| `MDocMacro` | enum | public | `Tools/generate-manual/MDoc/MDocMacro.swift:130-130` | — |
| `MDocMacro.Comment` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:139-139` | — |
| `MDocMacro.DocumentDate` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:160-160` | — |
| `MDocMacro.DocumentTitle` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:183-183` | — |
| `MDocMacro.OperatingSystem` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:221-221` | — |
| `MDocMacro.DocumentName` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:262-262` | — |
| `MDocMacro.DocumentDescription` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:283-283` | — |
| `MDocMacro.SectionHeader` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:309-309` | — |
| `MDocMacro.SubsectionHeader` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:331-331` | — |
| `MDocMacro.SectionReference` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:351-351` | — |
| `MDocMacro.CrossManualReference` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:368-368` | — |
| `MDocMacro.ParagraphBreak` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:386-386` | — |
| `MDocMacro.BeginList` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:428-428` | — |
| `MDocMacro.BeginList.ListStyle` | enum | public | `Tools/generate-manual/MDoc/MDocMacro.swift:430-430` | — |
| `MDocMacro.ListItem` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:536-536` | — |
| `MDocMacro.EndList` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:553-553` | — |
| `MDocMacro.WithoutTrailingSpace` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:573-573` | — |
| `MDocMacro.WithoutLeadingSpace` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:590-590` | — |
| `MDocMacro.Apostrophe` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:607-607` | — |
| `MDocMacro.CommandOption` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:642-642` | — |
| `MDocMacro.CommandModifier` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:665-665` | — |
| `MDocMacro.CommandArgument` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:690-690` | — |
| `MDocMacro.OptionalCommandLineComponent` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:713-713` | — |
| `MDocMacro.BeginOptionalCommandLineComponent` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:738-738` | — |
| `MDocMacro.EndOptionalCommandLineComponent` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:748-748` | — |
| `MDocMacro.InteractiveCommand` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:770-770` | — |
| `MDocMacro.EnvironmentVariable` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:788-788` | — |
| `MDocMacro.FilePath` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:807-807` | — |
| `MDocMacro.Author` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:879-879` | — |
| `MDocMacro.Hyperlink` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:904-904` | — |
| `MDocMacro.MailTo` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:924-924` | — |
| `MDocMacro.Emphasis` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:982-982` | — |
| `MDocMacro.Boldface` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1005-1005` | — |
| `MDocMacro.NormalText` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1023-1023` | — |
| `MDocMacro.BeginFont` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1042-1042` | — |
| `MDocMacro.BeginFont.FontStyle` | enum | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1044-1044` | — |
| `MDocMacro.EndFont` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1074-1074` | — |
| `MDocMacro.BeginTypographicDoubleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1095-1095` | — |
| `MDocMacro.EndTypographicDoubleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1105-1105` | — |
| `MDocMacro.BeginTypewriterDoubleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1126-1126` | — |
| `MDocMacro.EndTypewriterDoubleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1136-1136` | — |
| `MDocMacro.BeginSingleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1155-1155` | — |
| `MDocMacro.EndSingleQuotes` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1165-1165` | — |
| `MDocMacro.BeginParentheses` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1184-1184` | — |
| `MDocMacro.EndParentheses` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1194-1194` | — |
| `MDocMacro.BeginSquareBrackets` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1213-1213` | — |
| `MDocMacro.EndSquareBrackets` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1223-1223` | — |
| `MDocMacro.BeginCurlyBraces` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1242-1242` | — |
| `MDocMacro.EndCurlyBraces` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1252-1252` | — |
| `MDocMacro.BeginAngleBrackets` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1271-1271` | — |
| `MDocMacro.EndAngleBrackets` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1281-1281` | — |
| `MDocMacro.ExitStandard` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1303-1303` | — |
| `MDocMacro.AttUnix` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1345-1345` | — |
| `MDocMacro.BSD` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1370-1370` | — |
| `MDocMacro.BSDOS` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1397-1397` | — |
| `MDocMacro.NetBSD` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1417-1417` | — |
| `MDocMacro.FreeBSD` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1437-1437` | — |
| `MDocMacro.OpenBSD` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1457-1457` | — |
| `MDocMacro.DragonFly` | struct | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1477-1477` | — |
| `MDocSerializationContext` | struct | public | `Tools/generate-manual/MDoc/MDocSerializationContext.swift:13-13` | — |

## Stored properties

| owner | property | declared type | access | declared at |
|---|---|---|---|---|
| `Color` | `fav` | `ColorOptions` | internal | `Examples/color/Color.swift:16-17` |
| `Color` | `second` | `ColorOptions?` | internal | `Examples/color/Color.swift:19-21` |
| `CountLines` | `inputFile` | `URL?` | internal | `Examples/count-lines/CountLines.swift:18-21` |
| `CountLines` | `prefix` | `String?` | internal | `Examples/count-lines/CountLines.swift:23-24` |
| `CountLines` | `verbose` | — | internal | `Examples/count-lines/CountLines.swift:26-27` |
| `DefaultAsFlag` | `configuration` | — | internal | `Examples/default-as-flag/DefaultAsFlag.swift:16-16` |
| `DefaultAsFlag` | `stringFlag` | `String?` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:24-25` |
| `DefaultAsFlag` | `numberFlag` | `Int?` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:27-28` |
| `DefaultAsFlag` | `boolFlag` | `Bool?` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:30-31` |
| `DefaultAsFlag` | `transformFlag` | `String?` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:33-38` |
| `DefaultAsFlag` | `regular` | `String?` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:40-41` |
| `DefaultAsFlag` | `additionalArgs` | `[String]` | internal | `Examples/default-as-flag/DefaultAsFlag.swift:43-44` |
| `Math` | `configuration` | — | internal | `Examples/math/Math.swift:18-18` |
| `Options` | `hexadecimalOutput` | — | internal | `Examples/math/Math.swift:37-40` |
| `Options` | `values` | `[Int]` | internal | `Examples/math/Math.swift:42-44` |
| `Math.Add` | `configuration` | — | internal | `Examples/math/Math.swift:55-55` |
| `Math.Add` | `options` | `Options` | internal | `Examples/math/Math.swift:60-60` |
| `Math.Multiply` | `configuration` | — | internal | `Examples/math/Math.swift:69-69` |
| `Math.Multiply` | `options` | `Options` | internal | `Examples/math/Math.swift:73-73` |
| `Math.Statistics` | `configuration` | — | internal | `Examples/math/Math.swift:85-85` |
| `Math.Statistics.Average` | `configuration` | — | internal | `Examples/math/Math.swift:96-96` |
| `Math.Statistics.Average` | `kind` | `Kind` | internal | `Examples/math/Math.swift:105-106` |
| `Math.Statistics.Average` | `values` | `[Double]` | internal | `Examples/math/Math.swift:108-109` |
| `Math.Statistics.StandardDeviation` | `configuration` | — | internal | `Examples/math/Math.swift:168-168` |
| `Math.Statistics.StandardDeviation` | `values` | `[Double]` | internal | `Examples/math/Math.swift:172-173` |
| `Math.Statistics.Quantiles` | `configuration` | — | internal | `Examples/math/Math.swift:193-193` |
| `Math.Statistics.Quantiles` | `oneOfFour` | `String?` | internal | `Examples/math/Math.swift:196-198` |
| `Math.Statistics.Quantiles` | `customArg` | `String?` | internal | `Examples/math/Math.swift:200-205` |
| `Math.Statistics.Quantiles` | `customDeprecatedArg` | `String?` | internal | `Examples/math/Math.swift:207-214` |
| `Math.Statistics.Quantiles` | `values` | `[Double]` | internal | `Examples/math/Math.swift:216-217` |
| `Math.Statistics.Quantiles` | `testSuccessExitCode` | — | internal | `Examples/math/Math.swift:220-221` |
| `Math.Statistics.Quantiles` | `testFailureExitCode` | — | internal | `Examples/math/Math.swift:222-223` |
| `Math.Statistics.Quantiles` | `testValidationExitCode` | — | internal | `Examples/math/Math.swift:224-225` |
| `Math.Statistics.Quantiles` | `testCustomExitCode` | `Int32?` | internal | `Examples/math/Math.swift:226-227` |
| `Math.Statistics.Quantiles` | `file` | `String?` | internal | `Examples/math/Math.swift:230-231` |
| `Math.Statistics.Quantiles` | `directory` | `String?` | internal | `Examples/math/Math.swift:232-233` |
| `Math.Statistics.Quantiles` | `shell` | `String?` | internal | `Examples/math/Math.swift:235-238` |
| `Math.Statistics.Quantiles` | `custom` | `String?` | internal | `Examples/math/Math.swift:240-241` |
| `Math.Statistics.Quantiles` | `customDeprecated` | `String?` | internal | `Examples/math/Math.swift:243-247` |
| `Repeat` | `count` | `Int?` | internal | `Examples/repeat/Repeat.swift:16-17` |
| `Repeat` | `includeCounter` | — | internal | `Examples/repeat/Repeat.swift:19-20` |
| `Repeat` | `phrase` | `String` | internal | `Examples/repeat/Repeat.swift:22-23` |
| `SplitMix64` | `state` | `UInt64` | private | `Examples/roll/SplitMix64.swift:13-13` |
| `RollOptions` | `times` | — | internal | `Examples/roll/main.swift:15-16` |
| `RollOptions` | `sides` | — | internal | `Examples/roll/main.swift:18-24` |
| `RollOptions` | `seed` | `Int?` | internal | `Examples/roll/main.swift:26-27` |
| `RollOptions` | `verbose` | — | internal | `Examples/roll/main.swift:29-30` |
| `GenerateDoccReferencePlugin` | `pluginName` | — | internal | `Plugins/GenerateDoccReference/GenerateDoccReference.swift:17-17` |
| `GenerateDoccReferencePlugin` | `executableName` | — | internal | `Plugins/GenerateDoccReference/GenerateDoccReference.swift:18-18` |
| `GenerateDoccReferencePlugin` | `artifactName` | — | internal | `Plugins/GenerateDoccReference/GenerateDoccReference.swift:19-19` |
| `GenerateManualPlugin` | `pluginName` | — | internal | `Plugins/GenerateManual/GenerateManualPlugin.swift:17-17` |
| `GenerateManualPlugin` | `executableName` | — | internal | `Plugins/GenerateManual/GenerateManualPlugin.swift:18-18` |
| `GenerateManualPlugin` | `artifactName` | — | internal | `Plugins/GenerateManual/GenerateManualPlugin.swift:19-19` |
| `CompletionShell` | `rawValue` | `String` | public | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:18-18` |
| `CompletionShell` | `_requesting` | — | internal | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:61-61` |
| `CompletionShell` | `_requestingVersion` | — | internal | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:74-74` |
| `CompletionsGenerator` | `shell` | `CompletionShell` | internal | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:99-99` |
| `CompletionsGenerator` | `command` | `ParsableCommand.Type` | internal | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:100-100` |
| `Argument` | `_parsedValue` | `Parsed<Value>` | internal | `Sources/ArgumentParser/Parsable Properties/Argument.swift:48-48` |
| `ArgumentArrayParsingStrategy` | `base` | `ArgumentDefinition.ParsingStrategy` | internal | `Sources/ArgumentParser/Parsable Properties/Argument.swift:111-111` |
| `ArgumentHelp` | `abstract` | `String` | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:15-15` |
| `ArgumentHelp` | `discussion` | `String?` | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:18-18` |
| `ArgumentHelp` | `valueName` | `String?` | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:25-25` |
| `ArgumentHelp` | `visibility` | `ArgumentVisibility` | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:29-29` |
| `ArgumentHelp` | `argumentType` | `(any ExpressibleByArgument.Type)?` | public | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:45-45` |
| `ArgumentVisibility` | `base` | `Representation` | internal | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:22-22` |
| `ArgumentVisibility` | `ʼdefaultʼ` | — | public | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:25-25` |
| `ArgumentVisibility` | `hidden` | — | public | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:28-28` |
| `ArgumentVisibility` | `ʼprivateʼ` | — | public | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:31-31` |
| `CompletionKind` | `kind` | `Kind` | internal | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:48-48` |
| `ValidationError` | `message` | `String` | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:18-18` |
| `ExitCode` | `rawValue` | `Int32` | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:37-37` |
| `ExitCode` | `success` | — | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:49-49` |
| `ExitCode` | `failure` | — | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:52-52` |
| `ExitCode` | `validationFailure` | — | public | `Sources/ArgumentParser/Parsable Properties/Errors.swift:55-55` |
| `CleanExit` | `base` | `Representation` | internal | `Sources/ArgumentParser/Parsable Properties/Errors.swift:77-77` |
| `Flag` | `_parsedValue` | `Parsed<Value>` | internal | `Sources/ArgumentParser/Parsable Properties/Flag.swift:73-73` |
| `FlagInversion` | `base` | `Representation` | internal | `Sources/ArgumentParser/Parsable Properties/Flag.swift:141-141` |
| `FlagExclusivity` | `base` | `Representation` | internal | `Sources/ArgumentParser/Parsable Properties/Flag.swift:179-179` |
| `NameSpecification.Element` | `base` | `Representation` | internal | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:44-44` |
| `NameSpecification` | `elements` | `[Element]` | internal | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:111-111` |
| `Option` | `_parsedValue` | `Parsed<Value>` | internal | `Sources/ArgumentParser/Parsable Properties/Option.swift:53-53` |
| `SingleValueParsingStrategy` | `base` | `ArgumentDefinition.ParsingStrategy` | internal | `Sources/ArgumentParser/Parsable Properties/Option.swift:117-117` |
| `DefaultAsFlagParsingStrategy` | `base` | `ArgumentDefinition.ParsingStrategy` | internal | `Sources/ArgumentParser/Parsable Properties/Option.swift:169-169` |
| `ArrayParsingStrategy` | `base` | `ArgumentDefinition.ParsingStrategy` | internal | `Sources/ArgumentParser/Parsable Properties/Option.swift:208-208` |
| `OptionGroup` | `_parsedValue` | `Parsed<Value>` | internal | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:35-35` |
| `OptionGroup` | `_visibility` | `ArgumentVisibility` | internal | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:36-36` |
| `OptionGroup` | `_dummy` | `Bool` | internal | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:40-40` |
| `OptionGroup` | `title` | `String` | public | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:43-43` |
| `ParentCommand` | `_parsedValue` | `Parsed<Value>` | internal | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:44-44` |
| `CommandConfiguration` | `commandName` | `String?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:18-18` |
| `CommandConfiguration` | `_superCommandName` | `String?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:25-25` |
| `CommandConfiguration` | `abstract` | `String` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:28-28` |
| `CommandConfiguration` | `usage` | `String?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:36-36` |
| `CommandConfiguration` | `discussion` | `String` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:44-44` |
| `CommandConfiguration` | `helpBanner` | `String?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:53-53` |
| `CommandConfiguration` | `version` | `String` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:56-56` |
| `CommandConfiguration` | `shouldDisplay` | `Bool` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:60-60` |
| `CommandConfiguration` | `ungroupedSubcommands` | `[ParsableCommand.Type]` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:79-79` |
| `CommandConfiguration` | `groupedSubcommands` | `[CommandGroup]` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:82-82` |
| `CommandConfiguration` | `defaultSubcommand` | `ParsableCommand.Type?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:85-85` |
| `CommandConfiguration` | `helpNames` | `NameSpecification?` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:88-88` |
| `CommandConfiguration` | `aliases` | `[String]` | public | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:95-95` |
| `CommandGroup` | `name` | `String` | public | `Sources/ArgumentParser/Parsable Types/CommandGroup.swift:15-15` |
| `CommandGroup` | `subcommands` | `[ParsableCommand.Type]` | public | `Sources/ArgumentParser/Parsable Types/CommandGroup.swift:18-18` |
| `_WrappedParsableCommand` | `options` | `P` | internal | `Sources/ArgumentParser/Parsable Types/ParsableArguments.swift:56-56` |
| `DecodedArguments` | `type` | `ParsableArguments.Type` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:18-18` |
| `DecodedArguments` | `value` | `ParsableArguments` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:19-19` |
| `ArgumentDecoder` | `values` | `ParsedValues` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:38-38` |
| `ArgumentDecoder` | `usedOrigins` | `InputOrigin` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:39-39` |
| `ArgumentDecoder` | `nextCommandIndex` | — | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:40-40` |
| `ArgumentDecoder` | `previouslyDecoded` | `[DecodedArguments]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:41-41` |
| `ArgumentDecoder` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:43-43` |
| `ArgumentDecoder` | `userInfo` | `[CodingUserInfoKey: Any]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:45-45` |
| `ParsedArgumentsContainer` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:82-82` |
| `ParsedArgumentsContainer` | `decoder` | `ArgumentDecoder` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:84-84` |
| `SingleValueDecoder` | `userInfo` | `[CodingUserInfoKey: Any]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:174-174` |
| `SingleValueDecoder` | `underlying` | `ArgumentDecoder` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:175-175` |
| `SingleValueDecoder` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:176-176` |
| `SingleValueDecoder` | `key` | `InputKey` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:177-177` |
| `SingleValueDecoder` | `parsedElement` | `ParsedValues.Element?` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:178-178` |
| `SingleValueDecoder.SingleValueContainer` | `underlying` | `SingleValueDecoder` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:225-225` |
| `SingleValueDecoder.SingleValueContainer` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:226-226` |
| `SingleValueDecoder.SingleValueContainer` | `parsedElement` | `ParsedValues.Element?` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:227-227` |
| `SingleValueDecoder.UnkeyedContainer` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:251-251` |
| `SingleValueDecoder.UnkeyedContainer` | `parsedElement` | `ParsedValues.Element` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:252-252` |
| `SingleValueDecoder.UnkeyedContainer` | `array` | `ArrayWrapperProtocol` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:253-253` |
| `ArrayWrapper` | `base` | `[A]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:305-305` |
| `ArrayWrapper` | `currentIndex` | `Int` | internal | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:306-306` |
| `ArgumentDefinition.Help.Options` | `rawValue` | `UInt` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:47-47` |
| `ArgumentDefinition.Help.Options` | `isOptional` | — | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:49-49` |
| `ArgumentDefinition.Help.Options` | `isRepeating` | — | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:50-50` |
| `ArgumentDefinition.Help` | `options` | `Options` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:53-53` |
| `ArgumentDefinition.Help` | `defaultValue` | `String?` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:54-54` |
| `ArgumentDefinition.Help` | `keys` | `[InputKey]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:55-55` |
| `ArgumentDefinition.Help` | `allValueStrings` | `[String]` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:56-56` |
| `ArgumentDefinition.Help` | `isComposite` | `Bool` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:57-57` |
| `ArgumentDefinition.Help` | `abstract` | `String` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:58-58` |
| `ArgumentDefinition.Help` | `discussion` | `ArgumentDiscussion?` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:59-59` |
| `ArgumentDefinition.Help` | `valueName` | `String` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:60-60` |
| `ArgumentDefinition.Help` | `visibility` | `ArgumentVisibility` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:61-61` |
| `ArgumentDefinition.Help` | `parentTitle` | `String` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:62-62` |
| `ArgumentDefinition` | `kind` | `Kind` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:107-107` |
| `ArgumentDefinition` | `help` | `Help` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:108-108` |
| `ArgumentDefinition` | `completion` | `CompletionKind` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:109-109` |
| `ArgumentDefinition` | `parsingStrategy` | `ParsingStrategy` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:110-110` |
| `ArgumentDefinition` | `update` | `Update` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:111-111` |
| `ArgumentDefinition` | `initial` | `Initial` | internal | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:112-112` |
| `ArgumentSet` | `content` | `[ArgumentDefinition]` | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:22-22` |
| `ArgumentSet` | `namePositions` | `[Name: Int]` | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:23-23` |
| `LenientParser` | `command` | `ParsableCommand.Type` | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:256-256` |
| `LenientParser` | `argumentSet` | `ArgumentSet` | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:257-257` |
| `LenientParser` | `inputArguments` | `SplitArguments` | internal | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:258-258` |
| `CommandError` | `commandStack` | `[ParsableCommand.Type]` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:13-13` |
| `CommandError` | `parserError` | `ParserError` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:14-14` |
| `HelpRequested` | `visibility` | `ArgumentVisibility` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:18-18` |
| `CommandParser` | `commandTree` | `Tree<ParsableCommand.Type>` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:22-22` |
| `CommandParser` | `currentNode` | `Tree<ParsableCommand.Type>` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:23-23` |
| `CommandParser` | `decodedArguments` | `[DecodedArguments]` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:24-24` |
| `GenerateCompletions` | `generateCompletionScript` | `String` | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:436-436` |
| `AutodetectedGenerateCompletions` | `generateCompletionScript` | — | internal | `Sources/ArgumentParser/Parsing/CommandParser.swift:440-440` |
| `InputKey` | `name` | `String` | internal | `Sources/ArgumentParser/Parsing/InputKey.swift:20-20` |
| `InputKey` | `path` | `[String]` | internal | `Sources/ArgumentParser/Parsing/InputKey.swift:23-23` |
| `InputOrigin` | `_elements` | `Set<Element>` | private | `Sources/ArgumentParser/Parsing/InputOrigin.swift:61-61` |
| `ParsedValues.Element` | `key` | `InputKey` | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:17-17` |
| `ParsedValues.Element` | `value` | `Any?` | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:18-18` |
| `ParsedValues.Element` | `inputOrigin` | `InputOrigin` | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:20-20` |
| `ParsedValues.Element` | `shouldClearArrayIfParsed` | — | fileprivate | `Sources/ArgumentParser/Parsing/ParsedValues.swift:21-21` |
| `ParsedValues` | `elements` | `[InputKey: Element]` | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:25-25` |
| `ParsedValues` | `originalInput` | `[String]` | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:30-30` |
| `ParsedValues` | `capturedUnrecognizedArguments` | — | internal | `Sources/ArgumentParser/Parsing/ParsedValues.swift:33-33` |
| `SplitArguments.Element` | `value` | `Value` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:107-107` |
| `SplitArguments.Element` | `index` | `Index` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:108-108` |
| `SplitArguments.InputIndex` | `rawValue` | `Int` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:128-128` |
| `SplitArguments.Index` | `inputIndex` | `InputIndex` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:173-173` |
| `SplitArguments.Index` | `subIndex` | `SubIndex` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:174-174` |
| `SplitArguments` | `_elements` | `[Element]` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:182-182` |
| `SplitArguments` | `firstUnused` | `Int` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:183-183` |
| `SplitArguments` | `originalInput` | `[String]` | internal | `Sources/ArgumentParser/Parsing/SplitArguments.swift:186-186` |
| `DumpHelpGenerator` | `toolInfo` | `ToolInfoV0` | private | `Sources/ArgumentParser/Usage/DumpHelpGenerator.swift:15-15` |
| `HelpCommand` | `configuration` | — | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:13-13` |
| `HelpCommand` | `subcommands` | `[String]` | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:19-19` |
| `HelpCommand` | `help` | — | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:22-25` |
| `HelpCommand` | `commandStack` | `[ParsableCommand.Type]` | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:27-27` |
| `HelpCommand` | `visibility` | `ArgumentVisibility` | internal | `Sources/ArgumentParser/Usage/HelpCommand.swift:28-28` |
| `HelpGenerator` | `helpIndent` | — | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:13-13` |
| `HelpGenerator` | `labelColumnWidth` | — | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:14-14` |
| `HelpGenerator.Section.Element` | `label` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:19-19` |
| `HelpGenerator.Section.Element` | `abstract` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:20-20` |
| `HelpGenerator.Section.Element` | `discussion` | `ArgumentDiscussion?` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:21-21` |
| `HelpGenerator.Section` | `header` | `Header` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:131-131` |
| `HelpGenerator.Section` | `elements` | `[Element]` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:132-132` |
| `HelpGenerator.Section` | `isSubcommands` | `Bool` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:133-133` |
| `HelpGenerator.DiscussionSection` | `title` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:147-147` |
| `HelpGenerator.DiscussionSection` | `content` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:148-148` |
| `HelpGenerator` | `commandStack` | `[ParsableCommand.Type]` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:151-151` |
| `HelpGenerator` | `abstract` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:152-152` |
| `HelpGenerator` | `usage` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:153-153` |
| `HelpGenerator` | `helpBanner` | `String` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:154-154` |
| `HelpGenerator` | `sections` | `[Section]` | internal | `Sources/ArgumentParser/Usage/HelpGenerator.swift:155-155` |
| `UsageGenerator` | `toolName` | `String` | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:13-13` |
| `UsageGenerator` | `definition` | `ArgumentSet` | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:14-14` |
| `ErrorMessageGenerator` | `arguments` | `ArgumentSet` | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:175-175` |
| `ErrorMessageGenerator` | `error` | `ParserError` | internal | `Sources/ArgumentParser/Usage/UsageGenerator.swift:176-176` |
| `Mutex._Lock` | `_platformLock` | `PlatformLock` | internal | `Sources/ArgumentParser/Utilities/Mutex.swift:44-44` |
| `Mutex` | `_buffer` | `ManagedBuffer<State, _Lock.Primitive>` | private | `Sources/ArgumentParser/Utilities/Mutex.swift:104-104` |
| `CommandLine` | `_staticArguments` | `[String]` | internal | `Sources/ArgumentParser/Utilities/Platform.swift:16-16` |
| `Platform.Environment.Key` | `shell` | — | internal | `Sources/ArgumentParser/Utilities/Platform.swift:40-40` |
| `Platform.Environment.Key` | `columns` | — | internal | `Sources/ArgumentParser/Utilities/Platform.swift:41-41` |
| `Platform.Environment.Key` | `lines` | — | internal | `Sources/ArgumentParser/Utilities/Platform.swift:42-42` |
| `Platform.Environment.Key` | `shellName` | — | internal | `Sources/ArgumentParser/Utilities/Platform.swift:49-49` |
| `Platform.Environment.Key` | `shellVersion` | — | internal | `Sources/ArgumentParser/Utilities/Platform.swift:56-56` |
| `Platform.Environment.Key` | `rawValue` | `String` | internal | `Sources/ArgumentParser/Utilities/Platform.swift:58-58` |
| `Tree` | `element` | `Element` | internal | `Sources/ArgumentParser/Utilities/Tree.swift:13-13` |
| `Tree` | `parent` | `Tree?` | internal | `Sources/ArgumentParser/Utilities/Tree.swift:14-14` |
| `Tree` | `children` | `[Tree]` | internal | `Sources/ArgumentParser/Utilities/Tree.swift:15-15` |
| `AsyncCompletionsValidator.Error` | `invalidAsyncCompletions` | `[String]` | internal | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:17-17` |
| `CodingKeyValidator.Validator` | `argumentKeys` | `[InputKey]` | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:15-15` |
| `CodingKeyValidator.Validator` | `codingPath` | `[CodingKey]` | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:22-22` |
| `CodingKeyValidator.Validator` | `userInfo` | `[CodingUserInfoKey: Any]` | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:23-23` |
| `CodingKeyValidator.MissingKeysError` | `missingCodingKeys` | `[InputKey]` | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:50-50` |
| `CodingKeyValidator.InvalidDecoderError` | `type` | `ParsableArguments.Type` | internal | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:83-83` |
| `NonsenseFlagsValidator.Error` | `names` | `[String]` | internal | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:15-15` |
| `ParsableArgumentsValidationError` | `parsableArgumentsType` | `ParsableArguments.Type` | internal | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:54-54` |
| `ParsableArgumentsValidationError` | `underlayingErrors` | `[Error]` | internal | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:55-55` |
| `PositionalArgumentsValidator.Error` | `repeatedPositionalArgument` | `String` | internal | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:20-20` |
| `PositionalArgumentsValidator.Error` | `positionalArgumentFollowingRepeated` | `String` | internal | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:22-22` |
| `UniqueNamesValidator.Error` | `duplicateNames` | `[String: Int]` | internal | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:16-16` |
| `TestExpectation` | `fulfilled` | — | public | `Sources/ArgumentParserTestHelpers/TestHelpers+SwiftTesting.swift:27-27` |
| `ToolInfoHeader` | `serializationVersion` | `Int` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:21-21` |
| `ToolInfoV0` | `serializationVersion` | — | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:33-33` |
| `ToolInfoV0` | `command` | `CommandInfoV0` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:35-35` |
| `CommandInfoV0` | `superCommands` | `[String]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:46-46` |
| `CommandInfoV0` | `shouldDisplay` | `Bool` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:48-48` |
| `CommandInfoV0` | `commandName` | `String` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:51-51` |
| `CommandInfoV0` | `aliases` | `[String]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:53-53` |
| `CommandInfoV0` | `abstract` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:55-55` |
| `CommandInfoV0` | `discussion` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:57-57` |
| `CommandInfoV0` | `defaultSubcommand` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:61-61` |
| `CommandInfoV0` | `subcommands` | `[CommandInfoV0]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:63-63` |
| `CommandInfoV0` | `arguments` | `[ArgumentInfoV0]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:65-65` |
| `ArgumentInfoV0.NameInfoV0` | `kind` | `KindV0` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:129-129` |
| `ArgumentInfoV0.NameInfoV0` | `name` | `String` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:131-131` |
| `ArgumentInfoV0` | `kind` | `KindV0` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:188-188` |
| `ArgumentInfoV0` | `shouldDisplay` | `Bool` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:191-191` |
| `ArgumentInfoV0` | `sectionTitle` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:193-193` |
| `ArgumentInfoV0` | `isOptional` | `Bool` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:196-196` |
| `ArgumentInfoV0` | `isRepeating` | `Bool` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:198-198` |
| `ArgumentInfoV0` | `parsingStrategy` | `ParsingStrategyV0` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:201-201` |
| `ArgumentInfoV0` | `names` | `[NameInfoV0]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:204-204` |
| `ArgumentInfoV0` | `preferredName` | `NameInfoV0?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:206-206` |
| `ArgumentInfoV0` | `valueName` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:209-209` |
| `ArgumentInfoV0` | `defaultValue` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:211-211` |
| `ArgumentInfoV0` | `allValues` | `[String]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:217-217` |
| `ArgumentInfoV0` | `allValueDescriptions` | `[String: String]?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:224-224` |
| `ArgumentInfoV0` | `completionKind` | `CompletionKindV0?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:229-229` |
| `ArgumentInfoV0` | `abstract` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:232-232` |
| `ArgumentInfoV0` | `discussion` | `String?` | public | `Sources/ArgumentParserToolInfo/ToolInfo.swift:234-234` |
| `AsyncStatusCheck.Status` | `rawValue` | `UInt8` | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:19-19` |
| `AsyncStatusCheck` | `status` | `Status` | internal | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:25-26` |
| `Name` | `rawValue` | `String` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:23-23` |
| `Foo` | `first` | `Subgroup` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:63-64` |
| `Foo` | `second` | `Subgroup` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:66-67` |
| `Bar` | `firstName` | `Name` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:101-103` |
| `Bar` | `lastName` | `Name?` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:105-106` |
| `Qux` | `firstName` | `[Name]` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:149-150` |
| `Qux` | `lastName` | `[Name]` | internal | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:152-153` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformExplicitNil` | `showBinPath` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:24-25` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformNoExplicitNil` | `showBinPath` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:32-33` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformExplicitNil` | `showBinPath` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:40-43` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformNoExplicitNil` | `showBinPath` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:50-53` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagAndArguments` | `option` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:151-152` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagAndArguments` | `files` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:154-155` |
| `Main` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:23-23` |
| `Default` | `mode` | `Mode` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:34-34` |
| `DefaultSubcommandEndToEndTests.MyCommand` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:79-79` |
| `DefaultSubcommandEndToEndTests.MyCommand` | `foo` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:86-86` |
| `DefaultSubcommandEndToEndTests.MyCommand` | `options` | `CommonOptions` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:88-89` |
| `DefaultSubcommandEndToEndTests.CommonOptions` | `verbose` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:93-96` |
| `DefaultSubcommandEndToEndTests.Plugin` | `options` | `CommonOptions` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:100-100` |
| `DefaultSubcommandEndToEndTests.Plugin` | `pluginName` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:101-101` |
| `DefaultSubcommandEndToEndTests.Plugin` | `pluginArguments` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:103-104` |
| `DefaultSubcommandEndToEndTests.NonDefault` | `options` | `CommonOptions` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:108-108` |
| `DefaultSubcommandEndToEndTests.NonDefault` | `pluginName` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:109-109` |
| `DefaultSubcommandEndToEndTests.NonDefault` | `pluginArguments` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:111-112` |
| `DefaultSubcommandEndToEndTests.Other` | `options` | `CommonOptions` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:116-116` |
| `DefaultSubcommandEndToEndTests.Child` | `parent` | `MyCommand` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:120-120` |
| `DefaultSubcommandEndToEndTests.BadParent` | `notMyParent` | `Other` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:124-124` |
| `DefaultSubcommandEndToEndTests.RootWithPassthroughDefault` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:313-313` |
| `DefaultSubcommandEndToEndTests.PassthroughDefault` | `remaining` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:321-322` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:341-341` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.Nested` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:349-349` |
| `Foo.Name` | `rawValue` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:22-22` |
| `Foo` | `name` | `Name` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:24-25` |
| `Foo` | `max` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:26-27` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:64-65` |
| `Bar` | `format` | `Format` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:66-67` |
| `Bar` | `foo` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:68-69` |
| `Bar` | `bar` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:70-71` |
| `Bar_NextInput` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:247-248` |
| `Bar_NextInput` | `format` | `Format` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:249-250` |
| `Bar_NextInput` | `foo` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:251-252` |
| `Bar_NextInput` | `bar` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:253-254` |
| `Baz` | `int` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:301-301` |
| `Baz` | `int8` | `Int8` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:302-302` |
| `Baz` | `int16` | `Int16` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:303-303` |
| `Baz` | `int32` | `Int32` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:304-304` |
| `Baz` | `int64` | `Int64` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:305-305` |
| `Baz` | `uint` | `UInt` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:306-306` |
| `Baz` | `uint8` | `UInt8` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:307-307` |
| `Baz` | `uint16` | `UInt16` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:308-308` |
| `Baz` | `uint32` | `UInt32` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:309-309` |
| `Baz` | `uint64` | `UInt64` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:310-310` |
| `Baz` | `float` | `Float` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:312-312` |
| `Baz` | `double` | `Double` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:313-313` |
| `Baz` | `bool` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:315-315` |
| `Qux` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:405-406` |
| `OptionPropertyInitArguments_Default` | `data` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:447-448` |
| `OptionPropertyInitArguments_Default` | `transformedData` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:450-451` |
| `OptionPropertyInitArguments_NoDefault_NoTransform` | `data` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:457-458` |
| `OptionPropertyInitArguments_NoDefault_Transform` | `transformedData` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:464-465` |
| `ArgumentPropertyInitArguments_Default_NoTransform` | `data` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:549-550` |
| `ArgumentPropertyInitArguments_NoDefault_NoTransform` | `data` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:556-557` |
| `ArgumentPropertyInitArguments_Default_Transform` | `transformedData` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:563-564` |
| `ArgumentPropertyInitArguments_NoDefault_Transform` | `transformedData` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:570-571` |
| `Quux` | `letters` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:654-655` |
| `Quux` | `numbers` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:657-658` |
| `FlagPropertyInitArguments_Bool_Default` | `data` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:684-685` |
| `FlagPropertyInitArguments_Bool_NoDefault` | `data` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:689-690` |
| `FlagPropertyInitArguments_EnumerableFlag_Default` | `data` | `HasData` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:734-735` |
| `FlagPropertyInitArguments_EnumerableFlag_NoDefault` | `data` | `HasData` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:741-742` |
| `Main` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:786-786` |
| `Main.Options` | `letters` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:792-793` |
| `Main.Sub` | `numbers` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:797-798` |
| `Main.Sub` | `options` | `Main.Options` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:800-801` |
| `RequiredArray_Option_NoTransform` | `array` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:831-832` |
| `RequiredArray_Option_Transform` | `array` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:836-837` |
| `RequiredArray_Argument_NoTransform` | `array` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:841-842` |
| `RequiredArray_Argument_Transform` | `array` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:846-847` |
| `RequiredArray_Flag` | `array` | `[HasData]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:851-852` |
| `OptionPropertyDeprecatedInit_NoDefault` | `data` | `String` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:983-984` |
| `DefaultsEndToEndTests.TwoPaths` | `path1` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1007-1008` |
| `DefaultsEndToEndTests.TwoPaths` | `path2` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1010-1011` |
| `DefaultsEndToEndTests.TwoPaths` | `path3` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1013-1014` |
| `DefaultsEndToEndTests.TwoPaths` | `path4` | — | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1016-1017` |
| `DefaultsEndToEndTests.UnderscoredOptional` | `_arg` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1037-1038` |
| `DefaultsEndToEndTests.UnderscoredArray` | `_columns` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1042-1043` |
| `Bar` | `index` | `Index` | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:26-27` |
| `Baz` | `modeOption` | `Mode?` | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:63-63` |
| `Baz` | `modeArg` | `Mode?` | internal | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:64-64` |
| `Foo` | `toggle` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:21-21` |
| `Foo` | `name` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:22-22` |
| `Foo` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:23-23` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:52-52` |
| `Bar` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:53-53` |
| `Baz` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:69-69` |
| `Baz` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:70-70` |
| `LongOptionWithFile` | `out` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:86-86` |
| `LongOptionWithFile` | `file` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:87-87` |
| `LongOptionWithOptionalString` | `name` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:91-91` |
| `LongOptionWithOptionalString` | `file` | `String` | internal | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:92-92` |
| `Bar` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:21-22` |
| `Bar` | `extattr` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:24-25` |
| `Bar` | `extattr2` | `Bool?` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:27-28` |
| `Bar` | `logging` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:30-31` |
| `Foo` | `index` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:97-98` |
| `Foo` | `sandbox` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:99-100` |
| `Foo` | `requiredElement` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:101-102` |
| `Foo` | `optional` | `Bool?` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:103-104` |
| `Baz` | `color` | `Color` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:200-201` |
| `Baz` | `size` | `Size` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:203-204` |
| `Baz` | `shape` | `Shape?` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:206-207` |
| `Qux` | `color` | `[Color]` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:321-322` |
| `Qux` | `size` | `[Size]` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:324-325` |
| `RepeatOK` | `color` | `Color` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:363-364` |
| `RepeatOK` | `shape` | `Shape` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:366-367` |
| `RepeatOK` | `size` | `Size` | internal | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:369-370` |
| `Foo` | `file` | — | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:21-22` |
| `Foo` | `debug` | — | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:24-25` |
| `Foo` | `fdi` | — | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:27-28` |
| `Bar` | `debug` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:101-102` |
| `Baz` | `debug` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:134-136` |
| `Baz` | `verbose` | — | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:138-138` |
| `Qux` | `debug` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:176-177` |
| `Bar` | `file` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:21-22` |
| `Bar` | `force` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:24-25` |
| `Bar` | `input` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:27-28` |
| `LongNameWithSingleDashEndToEndTests.Issue327` | `args` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:113-116` |
| `LongNameWithSingleDashEndToEndTests.JoinedItem` | `arg` | `String` | internal | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:128-129` |
| `Foo` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:21-21` |
| `Foo` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:24-25` |
| `Foo.Build` | `foo` | `Foo` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:28-28` |
| `Foo.Build` | `input` | `String` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:30-31` |
| `Foo.Package` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:35-35` |
| `Foo.Package` | `force` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:40-41` |
| `Foo.Package.Clean` | `foo` | `Foo` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:44-44` |
| `Foo.Package.Clean` | `package` | `Package` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:45-45` |
| `Foo.Package.Config` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:49-49` |
| `Foo.Package.Config` | `foo` | `Foo` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:50-50` |
| `Foo.Package.Config` | `package` | `Package` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:51-51` |
| `Options` | `firstName` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:282-282` |
| `UniqueOptions` | `lastName` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:286-286` |
| `Super` | `options` | `Options` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:294-294` |
| `Super.Sub1` | `options` | `Options` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:297-297` |
| `Super.Sub2` | `options` | `UniqueOptions` | internal | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:301-301` |
| `ValidationConfirmations` | `inner` | `Confirmation?` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:19-19` |
| `ValidationConfirmations` | `outer` | `Confirmation?` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:20-20` |
| `ValidationConfirmations` | `command` | `Confirmation?` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:21-21` |
| `Inner` | `extraVerbiage` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:25-26` |
| `Inner` | `size` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:27-28` |
| `Inner` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:29-30` |
| `Outer` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:38-39` |
| `Outer` | `before` | `String` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:40-41` |
| `Outer` | `inner` | `Inner` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:42-43` |
| `Outer` | `after` | `String` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:44-45` |
| `Command` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:53-53` |
| `Command` | `outer` | `Outer` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:55-56` |
| `DuplicatedFlagGroupCustom` | `duplicated` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:130-131` |
| `DuplicatedFlagGroupCustomCommand` | `duplicated` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:135-135` |
| `DuplicatedFlagGroupCustomCommand` | `option` | `DuplicatedFlagGroupCustom` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:136-136` |
| `DuplicatedFlagGroupLong` | `duplicated` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:140-140` |
| `DuplicatedFlagGroupLongCommand` | `duplicated` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:144-145` |
| `DuplicatedFlagGroupLongCommand` | `option` | `DuplicatedFlagGroupLong` | internal | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:146-146` |
| `Foo.Name` | `rawValue` | `String` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:22-22` |
| `Foo` | `name` | `Name?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:24-24` |
| `Foo` | `max` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:25-25` |
| `Bar` | `name` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:64-64` |
| `Bar` | `format` | `Format?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:65-65` |
| `Bar` | `foo` | `String` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:66-66` |
| `Bar` | `bar` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:67-67` |
| `OptionalEndToEndTests.Command` | `testOption` | `Foo?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:238-244` |
| `OptionalEndToEndTests.Command` | `testArgument` | `Foo?` | internal | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:246-252` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:21-21` |
| `Baz` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:57-57` |
| `Baz` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:58-58` |
| `Qux` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:105-105` |
| `Wobble` | `count` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:149-149` |
| `Wobble` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:150-150` |
| `Flob` | `counts` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:204-204` |
| `BadlyFormed` | `numbers` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:240-240` |
| `BadlyFormed` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:241-241` |
| `PositionalEndToEndTests.HasRange` | `range` | `Range<Int>` | internal | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:272-272` |
| `Bar.Identifier` | `rawValue` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:22-22` |
| `Bar` | `identifier` | `Identifier` | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:25-25` |
| `LogLevel` | `rawValue` | `String` | internal | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:56-56` |
| `AllUnrecognizedArgs` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:24-24` |
| `AllUnrecognizedArgs` | `useFiles` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:25-25` |
| `AllUnrecognizedArgs` | `useStandardInput` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:26-26` |
| `AllUnrecognizedArgs` | `hoopla` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:27-27` |
| `AllUnrecognizedArgs` | `config` | — | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:28-28` |
| `AllUnrecognizedArgs` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:29-29` |
| `AllUnrecognizedRoot` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:85-85` |
| `AllUnrecognizedRoot.Child` | `includeExtras` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:88-88` |
| `AllUnrecognizedRoot.Child` | `config` | — | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:89-89` |
| `AllUnrecognizedRoot.Child` | `extras` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:90-90` |
| `AllUnrecognizedRoot.Child` | `root` | `AllUnrecognizedRoot` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:91-91` |
| `PostTerminatorArgs` | `useFiles` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:129-129` |
| `PostTerminatorArgs` | `useStandardInput` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:130-130` |
| `PostTerminatorArgs` | `config` | — | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:131-131` |
| `PostTerminatorArgs` | `title` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:132-132` |
| `PostTerminatorArgs` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:133-134` |
| `PassthroughArgs` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:185-185` |
| `PassthroughArgs` | `useFiles` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:186-186` |
| `PassthroughArgs` | `useStandardInput` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:187-187` |
| `PassthroughArgs` | `config` | — | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:188-188` |
| `PassthroughArgs` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:189-189` |
| `Bar` | `name` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:22-22` |
| `Foo` | `verbose` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:48-49` |
| `Baz` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:70-70` |
| `Baz` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:71-71` |
| `Outer` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:140-140` |
| `Inner` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:144-145` |
| `Inner` | `files` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:147-148` |
| `Qux` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:167-167` |
| `Qux` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:168-168` |
| `Qux` | `extra` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:169-169` |
| `Wobble.Name` | `value` | `String` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:277-277` |
| `Wobble` | `names` | `[Name]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:284-284` |
| `Wobble` | `moreNames` | `[Name]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:285-285` |
| `Wobble` | `evenMoreNames` | `[Name]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:287-287` |
| `Weazle` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:374-374` |
| `Weazle` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:375-375` |
| `PerformanceTest` | `bundleIdentifiers` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:403-403` |
| `Bar` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:21-22` |
| `Bar` | `file` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:24-25` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:27-28` |
| `Foo` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:91-92` |
| `Foo` | `file` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:94-95` |
| `Foo` | `city` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:97-98` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:21-21` |
| `Foo` | `count` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:67-67` |
| `Baz` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:110-110` |
| `Baz` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:111-111` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:21-21` |
| `Bar` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:22-22` |
| `Bar` | `input` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:23-23` |
| `Baz` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:62-62` |
| `Baz` | `format` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:63-63` |
| `Baz` | `input` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:64-64` |
| `AlmostAllArguments` | `a_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:24-24` |
| `AlmostAllArguments` | `a0` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:25-25` |
| `AlmostAllArguments` | `a1` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:26-26` |
| `AlmostAllArguments` | `a2_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:27-27` |
| `AlmostAllArguments` | `b_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:29-29` |
| `AlmostAllArguments` | `b1_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:30-30` |
| `AlmostAllArguments` | `b2` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:31-31` |
| `AlmostAllArguments` | `b3` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:32-32` |
| `AlmostAllArguments` | `b4` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:33-33` |
| `AlmostAllArguments` | `b5_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:34-34` |
| `AlmostAllArguments` | `b6_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:35-35` |
| `AlmostAllArguments` | `c0` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:37-37` |
| `AlmostAllArguments` | `c1` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:38-38` |
| `AlmostAllArguments` | `d2` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:40-40` |
| `AlmostAllArguments` | `d3` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:41-41` |
| `AlmostAllArguments` | `d4` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:42-42` |
| `AlmostAllArguments` | `e` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:44-44` |
| `AlmostAllArguments` | `e1` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:45-45` |
| `AlmostAllArguments` | `e2` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:46-46` |
| `AlmostAllArguments` | `e3` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:47-47` |
| `AlmostAllArguments` | `e4` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:48-48` |
| `AlmostAllArguments` | `e5` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:49-49` |
| `AlmostAllArguments` | `e6` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:50-50` |
| `AlmostAllArguments` | `e7` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:51-51` |
| `AlmostAllArguments` | `e8` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:52-52` |
| `AlmostAllArguments` | `e9` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:54-54` |
| `AlmostAllArguments` | `e10` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:55-55` |
| `AlmostAllArguments` | `e11` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:56-56` |
| `AlmostAllArguments` | `e12` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:57-57` |
| `AlmostAllArguments` | `e13` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:58-58` |
| `AlmostAllArguments` | `e14` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:59-59` |
| `AlmostAllArguments` | `e15` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:60-60` |
| `AllOptions` | `a_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:65-65` |
| `AllOptions` | `a1_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:66-66` |
| `AllOptions` | `a2` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:67-67` |
| `AllOptions` | `a3_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:68-68` |
| `AllOptions` | `a4` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:69-69` |
| `AllOptions` | `a5_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:70-70` |
| `AllOptions` | `a6_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:71-71` |
| `AllOptions` | `a7` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:72-72` |
| `AllOptions` | `a8` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:73-73` |
| `AllOptions` | `a9_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:74-74` |
| `AllOptions` | `a10` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:75-75` |
| `AllOptions` | `a11_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:76-76` |
| `AllOptions` | `a12` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:77-77` |
| `AllOptions` | `a13` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:78-78` |
| `AllOptions` | `b2` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:80-80` |
| `AllOptions` | `b4` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:81-81` |
| `AllOptions` | `b7` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:82-82` |
| `AllOptions` | `b8` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:83-83` |
| `AllOptions` | `b10` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:84-84` |
| `AllOptions` | `b12` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:85-85` |
| `AllOptions` | `b13` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:86-86` |
| `AllOptions` | `c_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:88-89` |
| `AllOptions` | `c1_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:90-91` |
| `AllOptions` | `c2` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:92-92` |
| `AllOptions` | `c3_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:94-94` |
| `AllOptions` | `c4` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:96-96` |
| `AllOptions` | `c5_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:97-97` |
| `AllOptions` | `c6_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:98-98` |
| `AllOptions` | `c7` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:100-100` |
| `AllOptions` | `c8` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:101-101` |
| `AllOptions` | `c9_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:102-102` |
| `AllOptions` | `c10` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:103-103` |
| `AllOptions` | `c11_newDefaultSyntax` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:104-104` |
| `AllOptions` | `c12` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:105-105` |
| `AllOptions` | `c13` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:106-106` |
| `AllOptions` | `d2` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:108-108` |
| `AllOptions` | `d4` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:110-110` |
| `AllOptions` | `d7` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:111-111` |
| `AllOptions` | `d8` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:112-112` |
| `AllOptions` | `d10` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:113-113` |
| `AllOptions` | `d12` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:114-114` |
| `AllOptions` | `d13` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:115-115` |
| `AllOptions` | `e` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:117-117` |
| `AllOptions` | `e1` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:118-118` |
| `AllOptions` | `e2` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:119-119` |
| `AllOptions` | `e3` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:120-120` |
| `AllOptions` | `e4` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:121-121` |
| `AllOptions` | `e5` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:122-122` |
| `AllOptions` | `e6` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:123-123` |
| `AllOptions` | `e7` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:124-124` |
| `AllOptions` | `e8` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:125-125` |
| `AllOptions` | `e9` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:126-126` |
| `AllOptions` | `e10` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:127-127` |
| `AllOptions` | `e11` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:128-128` |
| `AllOptions` | `e12` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:129-129` |
| `AllOptions` | `e13` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:130-130` |
| `AllOptions` | `f` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:132-133` |
| `AllOptions` | `f1` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:134-134` |
| `AllOptions` | `f2` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:136-137` |
| `AllOptions` | `f3` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:138-138` |
| `AllOptions` | `f4` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:139-139` |
| `AllOptions` | `f5` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:140-140` |
| `AllOptions` | `f6` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:141-141` |
| `AllOptions` | `f7` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:142-142` |
| `AllOptions` | `f8` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:143-143` |
| `AllOptions` | `f9` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:145-145` |
| `AllOptions` | `f10` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:146-146` |
| `AllOptions` | `f11` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:147-147` |
| `AllOptions` | `f12` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:148-148` |
| `AllOptions` | `f13` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:149-149` |
| `AllFlags` | `a_explicitFalse` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:158-158` |
| `AllFlags` | `a0_explicitFalse` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:159-159` |
| `AllFlags` | `a1_explicitFalse` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:160-160` |
| `AllFlags` | `a2_explicitFalse` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:161-161` |
| `AllFlags` | `b` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:163-164` |
| `AllFlags` | `b1` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:165-165` |
| `AllFlags` | `b2` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:166-166` |
| `AllFlags` | `b3` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:167-167` |
| `AllFlags` | `b4` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:169-169` |
| `AllFlags` | `b5` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:170-170` |
| `AllFlags` | `b6` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:171-171` |
| `AllFlags` | `b7` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:172-172` |
| `AllFlags` | `c_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:174-175` |
| `AllFlags` | `c1_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:176-177` |
| `AllFlags` | `c2_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:178-178` |
| `AllFlags` | `c3_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:180-181` |
| `AllFlags` | `c4_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:182-182` |
| `AllFlags` | `c5_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:183-184` |
| `AllFlags` | `c6_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:185-185` |
| `AllFlags` | `c7_newDefaultSyntax` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:187-187` |
| `AllFlags` | `d_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:189-190` |
| `AllFlags` | `d1_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:191-192` |
| `AllFlags` | `d2_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:193-193` |
| `AllFlags` | `d3_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:194-195` |
| `AllFlags` | `d4_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:196-196` |
| `AllFlags` | `d5_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:197-197` |
| `AllFlags` | `d6_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:199-199` |
| `AllFlags` | `d7_implicitNil` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:200-200` |
| `AllFlags` | `e` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:202-202` |
| `AllFlags` | `e0` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:203-203` |
| `AllFlags` | `e1` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:204-204` |
| `AllFlags` | `e2` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:205-205` |
| `AllFlags` | `f_newDefaultSyntax` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:207-207` |
| `AllFlags` | `f1` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:208-208` |
| `AllFlags` | `f2` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:209-209` |
| `AllFlags` | `f3_newDefaultSyntax` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:210-210` |
| `AllFlags` | `f4_newDefaultSyntax` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:211-211` |
| `AllFlags` | `f5` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:212-212` |
| `AllFlags` | `f6` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:213-213` |
| `AllFlags` | `f7_newDefaultSyntax` | `E` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:214-214` |
| `AllFlags` | `g` | `E?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:216-216` |
| `AllFlags` | `g1` | `E?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:217-217` |
| `AllFlags` | `g2` | `E?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:218-218` |
| `AllFlags` | `g3` | `E?` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:219-219` |
| `AllFlags` | `h` | `[E]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:221-221` |
| `AllFlags` | `h1` | `[E]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:222-222` |
| `AllFlags` | `h2` | `[E]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:223-223` |
| `AllFlags` | `h3` | `[E]` | internal | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:224-224` |
| `Foo` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:21-21` |
| `Foo` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:24-24` |
| `CommandA` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:28-28` |
| `CommandA` | `foo` | `Foo` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:30-30` |
| `CommandA` | `bar` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:32-32` |
| `CommandB` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:36-36` |
| `CommandB` | `foo` | `Foo` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:38-38` |
| `CommandB` | `baz` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:40-40` |
| `Math` | `operation` | `Operation` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:134-135` |
| `Math` | `verbose` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:137-138` |
| `Math` | `operands` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:140-141` |
| `Math` | `didRun` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:143-143` |
| `BaseCommand` | `baseFlagValue` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:173-173` |
| `BaseCommand` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:175-175` |
| `BaseCommand` | `baseFlag` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:180-181` |
| `BaseCommand.SubCommand` | `subFlagValue` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:192-192` |
| `BaseCommand.SubCommand` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:194-194` |
| `BaseCommand.SubCommand` | `subFlag` | `String` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:199-200` |
| `BaseCommand.SubCommand.SubSubCommand` | `didValidateExpectation` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:212-212` |
| `BaseCommand.SubCommand.SubSubCommand` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:214-214` |
| `BaseCommand.SubCommand.SubSubCommand` | `subSubFlag` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:218-219` |
| `A` | `configuration` | — | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:269-269` |
| `A.HasVersionFlag` | `version` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:274-274` |
| `A.NoVersionFlag` | `hello` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:278-278` |
| `FooOption` | `usageString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:40-40` |
| `FooOption` | `help` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:44-44` |
| `FooOption` | `string` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:47-50` |
| `BarOption` | `usageString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:55-55` |
| `BarOption` | `help` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:59-59` |
| `BarOption` | `strings` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:62-66` |
| `FooArgument` | `usageString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:125-125` |
| `FooArgument` | `help` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:129-129` |
| `FooArgument` | `string` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:135-138` |
| `BarArgument` | `usageString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:143-143` |
| `BarArgument` | `help` | `String` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:147-147` |
| `BarArgument` | `strings` | `[Int]` | internal | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:150-154` |
| `Qux` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:21-21` |
| `Qux` | `verbose` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:22-22` |
| `Qux` | `count` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:23-23` |
| `Quizzo` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:27-27` |
| `Quizzo` | `verbose` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:28-28` |
| `Quizzo` | `count` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:29-29` |
| `Hogeraa` | `fullName` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:69-69` |
| `Hogera` | `firstName` | `String` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:73-73` |
| `Hogera` | `hasLastName` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:74-74` |
| `Hogera` | `fullName` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:75-75` |
| `Piyo` | `firstName` | `String` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:82-82` |
| `Piyo` | `hasLastName` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:83-83` |
| `Piyo` | `fullName` | `String!` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:84-84` |
| `Foo` | `foo` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:149-149` |
| `Foo` | `config` | `Config?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:150-150` |
| `Foo` | `opt` | `OptionalArguments` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:151-151` |
| `Foo` | `def` | `DefaultedArguments` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:152-152` |
| `Config` | `name` | `String` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:156-156` |
| `Config` | `age` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:157-157` |
| `OptionalArguments` | `title` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:161-161` |
| `OptionalArguments` | `edition` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:162-162` |
| `DefaultedArguments` | `one` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:166-166` |
| `DefaultedArguments` | `two` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:167-167` |
| `Barr` | `baz` | `Baz?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:202-202` |
| `Bar` | `bar` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:206-206` |
| `Bar` | `baz` | `Baz?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:207-207` |
| `Bar` | `bazz` | `Bazz?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:208-208` |
| `Baz` | `name` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:218-218` |
| `Baz` | `age` | `Int!` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:219-219` |
| `Bazz` | `name` | `String?` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:223-223` |
| `Bazz` | `age` | `Int` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:224-224` |
| `Bamf` | `bamph` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:319-319` |
| `Bamf` | `bop` | `[String: String]` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:320-320` |
| `Bamf` | `bopp` | `[String: [String]]` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:321-321` |
| `Qiqi` | `qiqiqi` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:338-338` |
| `Qiqi` | `qiqii` | `Qiqii` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:339-339` |
| `Fry` | `c` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:365-365` |
| `Fry` | `toksVig` | `Vig` | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:366-366` |
| `Toks` | `a` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:370-370` |
| `Vig` | `b` | — | internal | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:374-374` |
| `Foo` | `usageString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:31-31` |
| `Foo` | `helpString` | `String` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:36-36` |
| `Foo` | `count` | `Int?` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:49-50` |
| `Foo` | `names` | `[String]` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:52-53` |
| `Foo` | `version` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:55-56` |
| `Foo` | `throwCustomError` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:58-59` |
| `Foo` | `showUsageOnly` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:61-62` |
| `Foo` | `failValidationSilently` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:64-65` |
| `Foo` | `failSilently` | `Bool` | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:67-68` |
| `FooCommand` | `foo` | — | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:162-163` |
| `FooCommand` | `bar` | — | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:164-165` |
| `ValidateCountingArguments` | `validateCallCount` | — | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:187-187` |
| `ValidateCountingCommand` | `validateCallCount` | — | internal | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:195-195` |
| `Simple` | `verbose` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:171-171` |
| `Simple` | `min` | `Int?` | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:172-172` |
| `Simple` | `max` | `Int` | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:173-173` |
| `Simple` | `helpText` | — | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:175-175` |
| `CustomHelp` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:197-197` |
| `NoHelp` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:220-220` |
| `NoHelp` | `count` | `Int` | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:224-224` |
| `SubCommandCustomHelp` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:254-254` |
| `SubCommandCustomHelp.ModifiedHelp` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:263-263` |
| `Package.Clean` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Clean.swift:16-17` |
| `Package.Config` | `configuration` | — | public | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:20-20` |
| `Package.Config.GetMirror` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:25-26` |
| `Package.Config.GetMirror` | `packageURL` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:28-30` |
| `Package.Config.SetMirror` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:35-36` |
| `Package.Config.SetMirror` | `mirrorURL` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:38-39` |
| `Package.Config.SetMirror` | `packageURL` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:41-43` |
| `Package.Config.UnsetMirror` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:48-49` |
| `Package.Config.UnsetMirror` | `mirrorURL` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:51-52` |
| `Package.Config.UnsetMirror` | `packageURL` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:54-56` |
| `Package.Describe` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:17-18` |
| `Package.Describe` | `type` | `OutputType` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:20-21` |
| `Package.GenerateXcodeProject` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:17-17` |
| `Package.GenerateXcodeProject` | `options` | `Options` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:20-21` |
| `Package.GenerateXcodeProject` | `enableCodeCoverage` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:23-24` |
| `Package.GenerateXcodeProject` | `legacySchemeGenerator` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:26-27` |
| `Package.GenerateXcodeProject` | `output` | `String?` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:29-30` |
| `Package.GenerateXcodeProject` | `skipExtraFiles` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:32-36` |
| `Package.GenerateXcodeProject` | `watch` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:38-42` |
| `Package.GenerateXcodeProject` | `xcconfigOverrides` | `String?` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:44-45` |
| `Options` | `buildPath` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:15-16` |
| `Options` | `configuration` | `Configuration` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:23-26` |
| `Options` | `automaticResolution` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:28-31` |
| `Options` | `indexStore` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:33-36` |
| `Options` | `packageManifestCaching` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:38-41` |
| `Options` | `prefetching` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:43-44` |
| `Options` | `sandbox` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:46-49` |
| `Options` | `pubgrubResolver` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:51-54` |
| `Options` | `staticSwiftStdlib` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:55-58` |
| `Options` | `packagePath` | `String` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:59-60` |
| `Options` | `sanitize` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:62-63` |
| `Options` | `skipUpdate` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:65-67` |
| `Options` | `verbose` | `Bool` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:69-72` |
| `Options` | `cCompilerFlags` | `[String]` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:74-80` |
| `Options` | `cxxCompilerFlags` | `[String]` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:82-88` |
| `Options` | `linkerFlags` | `[String]` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:90-96` |
| `Options` | `swiftCompilerFlags` | `[String]` | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:98-104` |
| `Package` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:108-108` |
| `Package.Hidden` | `configuration` | — | internal | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:117-117` |
| `ArgumentParserToolInfoTests` | `examplesDirectory` | — | internal | `Tests/ArgumentParserToolInfoTests/ArgumentParserToolInfoTests.swift:65-65` |
| `ArgumentParserToolInfoTests` | `examples` | `[URL]` | internal | `Tests/ArgumentParserToolInfoTests/ArgumentParserToolInfoTests.swift:69-69` |
| `SerializedTests.CompletionScriptTests.Path` | `path` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:41-41` |
| `SerializedTests.CompletionScriptTests.NestedArguments` | `nestedArgument` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:63-64` |
| `SerializedTests.CompletionScriptTests.Base` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:68-68` |
| `SerializedTests.CompletionScriptTests.Base` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:72-72` |
| `SerializedTests.CompletionScriptTests.Base` | `kind` | `Kind` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:73-73` |
| `SerializedTests.CompletionScriptTests.Base` | `otherKind` | `Kind` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:74-74` |
| `SerializedTests.CompletionScriptTests.Base` | `path1` | `Path` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:76-76` |
| `SerializedTests.CompletionScriptTests.Base` | `path2` | `Path?` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:77-77` |
| `SerializedTests.CompletionScriptTests.Base` | `path3` | `Path` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:78-78` |
| `SerializedTests.CompletionScriptTests.Base` | `verbose` | — | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:80-80` |
| `SerializedTests.CompletionScriptTests.Base` | `allowedKinds` | `[Kind]` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:81-81` |
| `SerializedTests.CompletionScriptTests.Base` | `kindCounter` | `Int` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:82-82` |
| `SerializedTests.CompletionScriptTests.Base` | `rep1` | `[String]` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:84-84` |
| `SerializedTests.CompletionScriptTests.Base` | `rep2` | `[String]` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:85-85` |
| `SerializedTests.CompletionScriptTests.Base` | `argument` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:87-88` |
| `SerializedTests.CompletionScriptTests.Base` | `nested` | `NestedArguments` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:89-89` |
| `SerializedTests.CompletionScriptTests.Base.SubCommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:92-92` |
| `SerializedTests.CompletionScriptTests.Base.HiddenChild` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:97-97` |
| `SerializedTests.CompletionScriptTests.Base.EscapedCommand` | `one` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:101-107` |
| `SerializedTests.CompletionScriptTests.Base.EscapedCommand` | `two` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:109-110` |
| `SerializedTests.CompletionScriptTests.Custom` | `one` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:160-164` |
| `SerializedTests.CompletionScriptTests.Custom` | `two` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:166-167` |
| `SerializedTests.CompletionScriptTests.Custom` | `three` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:169-173` |
| `SerializedTests.CompletionScriptTests.Custom` | `nested` | `NestedArguments` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:175-175` |
| `SerializedTests.CompletionScriptTests.Custom.NestedArguments` | `four` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:178-179` |
| `SerializedTests.CompletionScriptTests.CustomAsync` | `five` | `String` | internal | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:184-187` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:46-46` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `binPath` | `String?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:52-53` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:55-56` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `verbose` | `Bool?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:58-59` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `logLevel` | `String?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:61-66` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `help` | `Bool` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:68-69` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | `input` | `String` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:71-72` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:29-29` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | `binPath` | `String?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:33-34` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:36-37` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | `verbose` | `Bool?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:39-40` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | `input` | `String` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:42-43` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:47-47` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | `outputDir` | `String?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:52-57` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | `level` | `String?` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:59-64` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | `debug` | `Bool` | internal | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:66-67` |
| `DumpHelpGenerationTests.A` | `enumeratedOption` | `TestEnum` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:63-64` |
| `DumpHelpGenerationTests.A` | `enumeratedOptionWithDefaultValue` | `TestEnum` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:66-67` |
| `DumpHelpGenerationTests.A` | `noHelpOption` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:69-70` |
| `DumpHelpGenerationTests.A` | `intOption` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:72-73` |
| `DumpHelpGenerationTests.A` | `intOptionWithDefaultValue` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:75-76` |
| `DumpHelpGenerationTests.A` | `arg` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:78-79` |
| `DumpHelpGenerationTests.A` | `argWithHelp` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:81-82` |
| `DumpHelpGenerationTests.A` | `argWithDefaultValue` | `Int` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:84-85` |
| `DumpHelpGenerationTests.Options` | `verbose` | — | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:89-90` |
| `DumpHelpGenerationTests.Options` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:92-93` |
| `DumpHelpGenerationTests.B` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:97-98` |
| `DumpHelpGenerationTests.C` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:102-102` |
| `DumpHelpGenerationTests.C` | `color` | `Color` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:121-122` |
| `DumpHelpGenerationTests.C` | `defaultColor` | `Color` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:124-125` |
| `DumpHelpGenerationTests.C` | `opt` | `Color?` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:127-128` |
| `DumpHelpGenerationTests.C` | `extra` | `Color` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:130-134` |
| `DumpHelpGenerationTests.C` | `discussion` | `String` | internal | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:136-137` |
| `ErrorCase` | `id` | `String` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:18-18` |
| `ErrorCase` | `arguments` | `[String]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:19-19` |
| `ErrorCase` | `expected` | `String` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:20-20` |
| `Bar` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:29-29` |
| `Bar` | `format` | `String` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:30-30` |
| `ErrorMessageTests` | `barCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:34-34` |
| `Foo` | `format` | `Format` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:109-110` |
| `Foo` | `name` | `Name?` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:111-112` |
| `EnumWithFewCasesArrayArgument` | `formats` | `[Format]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:116-117` |
| `EnumWithManyCasesArrayArgument` | `names` | `[Name]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:121-122` |
| `EnumWithIntRawValue` | `counter` | `Counter` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:126-126` |
| `ErrorMessageTests` | `fooCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:130-130` |
| `Baz` | `verbose` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:209-210` |
| `Qux` | `firstNumber` | `Int` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:223-224` |
| `Qux` | `secondNumber` | `Int` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:226-227` |
| `ErrorMessageTests` | `quxCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:231-231` |
| `Qwz` | `name` | `String?` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:253-253` |
| `Qwz` | `title` | `String?` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:254-254` |
| `ErrorMessageTests` | `qwzCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:258-258` |
| `Options` | `behaviour` | `OutputBehaviour` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:300-301` |
| `Options` | `bool` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:303-303` |
| `OptOptions` | `behaviour` | `OutputBehaviour?` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:315-316` |
| `ErrorMessageTests` | `optionsCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:320-320` |
| `EmptyArray` | `array` | `[String]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:362-363` |
| `EmptyArray` | `verbose` | — | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:365-366` |
| `ErrorMessageTests` | `emptyArrayCases` | `[ErrorCase]` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:370-370` |
| `Repeat` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:402-402` |
| `Repeat` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:403-403` |
| `ExitCodeTests.C` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:26-26` |
| `HelpGenerationTests.AtArgumentTransform.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:27-28` |
| `HelpGenerationTests.AtArgumentTransform.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:32-33` |
| `HelpGenerationTests.AtArgumentTransform.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:37-38` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:42-43` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:47-48` |
| `HelpGenerationTests.AtArgumentTransform.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:52-53` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:57-58` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:62-63` |
| `HelpGenerationTests.AtArgumentEBA.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:208-209` |
| `HelpGenerationTests.AtArgumentEBA.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:213-214` |
| `HelpGenerationTests.AtArgumentEBA.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:218-219` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:223-224` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:229-230` |
| `HelpGenerationTests.AtArgumentEBA.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:234-235` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:239-240` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:244-245` |
| `HelpGenerationTests.AtArgumentEBATransform.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:374-375` |
| `HelpGenerationTests.AtArgumentEBATransform.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:379-380` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:384-385` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:389-390` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:394-395` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:399-400` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:404-405` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:409-410` |
| `HelpGenerationTests.AtOptionTransform.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:27-28` |
| `HelpGenerationTests.AtOptionTransform.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:32-33` |
| `HelpGenerationTests.AtOptionTransform.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:37-38` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:42-43` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:47-48` |
| `HelpGenerationTests.AtOptionTransform.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:52-53` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:57-58` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:62-63` |
| `HelpGenerationTests.AtOptionEBA.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:184-185` |
| `HelpGenerationTests.AtOptionEBA.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:189-190` |
| `HelpGenerationTests.AtOptionEBA.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:194-195` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:199-200` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:205-206` |
| `HelpGenerationTests.AtOptionEBA.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:210-211` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:215-216` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:220-221` |
| `HelpGenerationTests.AtOptionEBATransform.BareNoDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:329-330` |
| `HelpGenerationTests.AtOptionEBATransform.BareDefault` | `arg0` | `A` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:334-335` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalNoDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:339-340` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefaultNil` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:344-345` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefault` | `arg0` | `A?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:349-350` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayNoDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:354-355` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefaultEmpty` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:359-360` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefault` | `arg0` | `[A]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:364-365` |
| `HelpGenerationTests.BasicDefaultAsFlag` | `stringFlag` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:20-22` |
| `HelpGenerationTests.BasicDefaultAsFlag` | `numberFlag` | `Int?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:24-25` |
| `HelpGenerationTests.BasicDefaultAsFlag` | `boolFlag` | `Bool?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:27-28` |
| `HelpGenerationTests.BasicDefaultAsFlag` | `transformFlag` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:30-33` |
| `HelpGenerationTests.BasicDefaultAsFlag` | `regular` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:35-36` |
| `HelpGenerationTests.DefaultAsFlagWithShortNames` | `shortAndLong` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:65-68` |
| `HelpGenerationTests.DefaultAsFlagWithShortNames` | `shortOnly` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:70-73` |
| `HelpGenerationTests.MixedOptionTypes` | `flag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:92-93` |
| `HelpGenerationTests.MixedOptionTypes` | `defaultAsFlag` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:95-96` |
| `HelpGenerationTests.MixedOptionTypes` | `regular` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:98-99` |
| `HelpGenerationTests.MixedOptionTypes` | `positional` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:101-102` |
| `HelpGenerationTests.Flags` | `verbose` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:22-23` |
| `HelpGenerationTests.Flags` | `oversharing` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:25-26` |
| `HelpGenerationTests.Options` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:30-31` |
| `HelpGenerationTests.Options` | `age` | `Int` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:33-34` |
| `HelpGenerationTests.FlagsAndOptions` | `experimental` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:38-39` |
| `HelpGenerationTests.FlagsAndOptions` | `prefix` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:41-42` |
| `HelpGenerationTests.ArgsAndFlags` | `name` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:46-47` |
| `HelpGenerationTests.ArgsAndFlags` | `title` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:49-50` |
| `HelpGenerationTests.ArgsAndFlags` | `existingUser` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:52-53` |
| `HelpGenerationTests.AllVisible` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:57-58` |
| `HelpGenerationTests.AllVisible` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:60-61` |
| `HelpGenerationTests.AllVisible` | `flagsAndOptions` | `FlagsAndOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:63-64` |
| `HelpGenerationTests.AllVisible` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:66-67` |
| `HelpGenerationTests.ContainsOptionGroup` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:71-72` |
| `HelpGenerationTests.ContainsOptionGroup` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:74-75` |
| `HelpGenerationTests.Combined` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:130-131` |
| `HelpGenerationTests.Combined` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:133-134` |
| `HelpGenerationTests.Combined` | `flagsAndOptions` | `FlagsAndOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:136-137` |
| `HelpGenerationTests.Combined` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:139-140` |
| `HelpGenerationTests.HiddenGroups` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:191-192` |
| `HelpGenerationTests.HiddenGroups` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:194-195` |
| `HelpGenerationTests.HiddenGroups` | `flagsAndOptions` | `FlagsAndOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:197-198` |
| `HelpGenerationTests.HiddenGroups` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:200-201` |
| `HelpGenerationTests.NestedGroups` | `flagsAndOptions` | `FlagsAndOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:237-238` |
| `HelpGenerationTests.NestedGroups` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:240-241` |
| `HelpGenerationTests.NestedHiddenGroups` | `nested` | `NestedGroups` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:245-246` |
| `HelpGenerationTests.ParentWithGroups` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:278-279` |
| `HelpGenerationTests.ParentWithGroups` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:281-282` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | `flags` | `Flags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:285-286` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:288-289` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | `argsAndFlags` | `ArgsAndFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:291-292` |
| `HelpGenerationTests.GroupsWithUnnamedGroups` | `extras` | `ContainsOptionGroup` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:391-392` |
| `HelpGenerationTests.GroupsWithNamedGroups` | `extras` | `ContainsOptionGroup` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:416-417` |
| `HelpGenerationTests.Root` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:22-22` |
| `HelpGenerationTests.Root.Inherits` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:29-29` |
| `HelpGenerationTests.Root.Inherits.Nested` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:34-34` |
| `HelpGenerationTests.Root.Overrides` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:40-40` |
| `HelpGenerationTests.Root.Overrides.Nested` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:46-46` |
| `HelpGenerationTests.Root.Suppresses` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:52-52` |
| `HelpGenerationTests.NoBanner` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:148-148` |
| `HelpGenerationTests.VerbatimBanner` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:168-168` |
| `HelpGenerationTests.BannerNoAbstract` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:199-199` |
| `HelpGenerationTests.A` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:40-40` |
| `HelpGenerationTests.A` | `title` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:41-41` |
| `HelpGenerationTests.B` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:59-59` |
| `HelpGenerationTests.B` | `title` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:60-60` |
| `HelpGenerationTests.B` | `hiddenName` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:62-62` |
| `HelpGenerationTests.B` | `hiddenTitle` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:63-63` |
| `HelpGenerationTests.B` | `hiddenFlag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:64-64` |
| `HelpGenerationTests.B` | `hiddenInvertedFlag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:65-65` |
| `HelpGenerationTests.C` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:103-107` |
| `HelpGenerationTests.Issue27` | `two` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:125-126` |
| `HelpGenerationTests.Issue27` | `three` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:127-128` |
| `HelpGenerationTests.Issue27` | `four` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:129-130` |
| `HelpGenerationTests.Issue27` | `five` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:131-132` |
| `HelpGenerationTests.D` | `occupation` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:171-172` |
| `HelpGenerationTests.D` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:174-175` |
| `HelpGenerationTests.D` | `age` | `Int` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:177-178` |
| `HelpGenerationTests.D` | `logging` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:180-181` |
| `HelpGenerationTests.D` | `lucky` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:183-186` |
| `HelpGenerationTests.D` | `nda` | `OptionFlags` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:188-189` |
| `HelpGenerationTests.D` | `degree` | `Degree` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:191-192` |
| `HelpGenerationTests.D` | `directory` | `URL` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:194-195` |
| `HelpGenerationTests.D` | `manual` | `Manual` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:201-202` |
| `HelpGenerationTests.D` | `unspecial` | `UnspecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:207-208` |
| `HelpGenerationTests.D` | `special` | `SpecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:214-215` |
| `HelpGenerationTests.E` | `behaviour` | `OutputBehaviour` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:253-254` |
| `HelpGenerationTests.F` | `behaviour` | `OutputBehaviour` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:266-267` |
| `HelpGenerationTests.G` | `flag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:271-272` |
| `HelpGenerationTests.H.ShortCommand` | `configuration` | `CommandConfiguration` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:314-314` |
| `HelpGenerationTests.H.AnotherCommandWithVeryLongName` | `configuration` | `CommandConfiguration` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:318-318` |
| `HelpGenerationTests.H.AnotherCommand` | `someOptionWithVeryLongName` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:322-323` |
| `HelpGenerationTests.H.AnotherCommand` | `option` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:325-326` |
| `HelpGenerationTests.H.AnotherCommand` | `argumentWithVeryLongNameAndHelp` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:328-329` |
| `HelpGenerationTests.H.AnotherCommand` | `argumentWithVeryLongName` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:331-332` |
| `HelpGenerationTests.H.AnotherCommand` | `argument` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:334-335` |
| `HelpGenerationTests.H` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:337-337` |
| `HelpGenerationTests.I` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:382-382` |
| `HelpGenerationTests.J` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:400-400` |
| `HelpGenerationTests.K` | `paths` | `[String]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:421-422` |
| `HelpGenerationTests.L` | `time` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:447-454` |
| `HelpGenerationTests.N` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:474-474` |
| `HelpGenerationTests.P` | `o` | `[O]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:507-508` |
| `HelpGenerationTests.P` | `remainder` | `[O]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:510-511` |
| `HelpGenerationTests.Foo` | `configuration` | — | public | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:531-531` |
| `HelpGenerationTests.Foo` | `fooName` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:539-540` |
| `HelpGenerationTests.Bar` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:546-546` |
| `HelpGenerationTests.Bar` | `barStrength` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:552-553` |
| `HelpGenerationTests.WithSubgroups` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:575-575` |
| `HelpGenerationTests.OnlySubgroups` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:612-612` |
| `HelpGenerationTests.OptionsToHide` | `verbose` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:651-652` |
| `HelpGenerationTests.OptionsToHide` | `customName` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:654-655` |
| `HelpGenerationTests.OptionsToHide` | `hiddenOption` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:657-658` |
| `HelpGenerationTests.OptionsToHide` | `privateArg` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:660-661` |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:666-666` |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | `hideMe` | `OptionsToHide` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:669-670` |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | `timeout` | `Int?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:672-673` |
| `HelpGenerationTests.HideOptionGroupDriver` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:677-677` |
| `HelpGenerationTests.HideOptionGroupDriver` | `hideMe` | `OptionsToHide` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:680-681` |
| `HelpGenerationTests.HideOptionGroupDriver` | `timeout` | `Int?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:683-684` |
| `HelpGenerationTests.PrivateOptionGroupDriver` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:688-688` |
| `HelpGenerationTests.PrivateOptionGroupDriver` | `hideMe` | `OptionsToHide` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:691-692` |
| `HelpGenerationTests.PrivateOptionGroupDriver` | `timeout` | `Int?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:694-695` |
| `HelpGenerationTests.AllValues.Manual` | `allValueStrings` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:755-755` |
| `HelpGenerationTests.AllValues` | `manualArgument` | `Manual` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:767-767` |
| `HelpGenerationTests.AllValues` | `manualOption` | `Manual` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:768-768` |
| `HelpGenerationTests.AllValues` | `unspecializedSynthesizedArgument` | `UnspecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:770-770` |
| `HelpGenerationTests.AllValues` | `unspecializedSynthesizedOption` | `UnspecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:771-771` |
| `HelpGenerationTests.AllValues` | `specializedSynthesizedArgument` | `SpecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:773-773` |
| `HelpGenerationTests.AllValues` | `specializedSynthesizedOption` | `SpecializedSynthesized` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:774-774` |
| `HelpGenerationTests.Q` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:808-808` |
| `HelpGenerationTests.Q` | `title` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:809-809` |
| `HelpGenerationTests.Q` | `privateName` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:811-811` |
| `HelpGenerationTests.Q` | `privateTitle` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:812-812` |
| `HelpGenerationTests.Q` | `privateFlag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:813-813` |
| `HelpGenerationTests.Q` | `privateInvertedFlag` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:814-814` |
| `HelpGenerationTests.ParserBug` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:837-837` |
| `HelpGenerationTests.ParserBug.CommonOptions` | `example` | `Bool` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:842-843` |
| `HelpGenerationTests.ParserBug.Sub` | `commonOptions` | `CommonOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:847-848` |
| `HelpGenerationTests.ParserBug.Sub` | `argument` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:850-851` |
| `HelpGenerationTests.NonCustomUsage.ExampleSubcommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:875-875` |
| `HelpGenerationTests.NonCustomUsage.ExampleSubcommand` | `output` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:876-876` |
| `HelpGenerationTests.NonCustomUsage` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:879-879` |
| `HelpGenerationTests.NonCustomUsage` | `file` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:882-882` |
| `HelpGenerationTests.NonCustomUsage` | `verboseMode` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:883-883` |
| `HelpGenerationTests.CustomUsageShort` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:887-887` |
| `HelpGenerationTests.CustomUsageShort` | `file` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:892-892` |
| `HelpGenerationTests.CustomUsageShort` | `verboseMode` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:893-893` |
| `HelpGenerationTests.CustomUsageLong` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:897-897` |
| `HelpGenerationTests.CustomUsageLong` | `file` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:904-904` |
| `HelpGenerationTests.CustomUsageLong` | `verboseMode` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:905-905` |
| `HelpGenerationTests.CustomUsageHidden` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:909-909` |
| `HelpGenerationTests.CustomUsageHidden` | `file` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:911-911` |
| `HelpGenerationTests.CustomUsageHidden` | `verboseMode` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:912-912` |
| `HelpGenerationTests.CustomOption` | `opt` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1083-1083` |
| `HelpGenerationTests.CustomOptionAsListWithSingleDefaultValue` | `opt` | `[OptionValues]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1103-1105` |
| `HelpGenerationTests.CustomOptionAsListWithMultipleDefaultValue` | `opt` | `[OptionValues]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1127-1129` |
| `HelpGenerationTests.CustomOptionAsListWithEmptyArrayAsDefault` | `opt` | `[OptionValues]` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1152-1154` |
| `HelpGenerationTests.CustomOptionWithDefault` | `opt` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1177-1178` |
| `HelpGenerationTests.Optional` | `optional` | `OptionValues?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1199-1199` |
| `HelpGenerationTests.NoAbstract` | `a` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1219-1219` |
| `HelpGenerationTests.NoAbstract` | `b` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1220-1220` |
| `HelpGenerationTests.Preamble` | `a` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1245-1255` |
| `HelpGenerationTests.Preamble` | `b` | `OptionValues?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1257-1264` |
| `HelpGenerationTests.HelpTextComparison` | `enumerable` | `OptionValues` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1299-1300` |
| `HelpGenerationTests.HelpTextComparison` | `values` | `OptionWithoutEnumerationHelpText` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1302-1304` |
| `HelpGenerationTests.EmptyCommand` | `empty` | `Empty` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1340-1340` |
| `HelpGenerationTests.LongLabelHelp` | `argument` | `Cases` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1381-1384` |
| `HelpGenerationTests.LongLabelHelpWithOptionDescription` | `argument` | `Cases` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1411-1418` |
| `HelpGenerationTests.WideHelp` | `argument` | `String?` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1450-1451` |
| `HelpGenerationTests.OptionGroupOptions` | `num` | `Int` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1506-1507` |
| `HelpGenerationTests.OptionGroupCommand` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1511-1511` |
| `HelpGenerationTests.OptionGroupCommand` | `options` | `OptionGroupOptions` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1513-1514` |
| `HelpGenerationTests.OptionGroupCommand` | `arg` | `String` | internal | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1516-1517` |
| `InputOriginTests.IsDefaultTestData` | `id` | `String` | internal | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:21-21` |
| `InputOriginTests.IsDefaultTestData` | `elements` | `[InputOrigin.Element]` | internal | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:22-22` |
| `InputOriginTests.IsDefaultTestData` | `expectedIsDefaultValue` | `Bool` | internal | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:23-23` |
| `MirrorTests.Foo` | `foo` | `String?` | internal | `Tests/ArgumentParserUnitTests/MirrorTests.swift:18-18` |
| `MirrorTests.Foo` | `bar` | `String` | internal | `Tests/ArgumentParserUnitTests/MirrorTests.swift:19-19` |
| `MirrorTests.Foo` | `baz` | `String!` | internal | `Tests/ArgumentParserUnitTests/MirrorTests.swift:20-20` |
| `ParsableArgumentsValidationTests.A` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:19-20` |
| `ParsableArgumentsValidationTests.A` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:22-23` |
| `ParsableArgumentsValidationTests.B` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:34-35` |
| `ParsableArgumentsValidationTests.B` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:37-38` |
| `ParsableArgumentsValidationTests.C` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:44-45` |
| `ParsableArgumentsValidationTests.C` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:47-48` |
| `ParsableArgumentsValidationTests.D` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:58-59` |
| `ParsableArgumentsValidationTests.D` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:61-62` |
| `ParsableArgumentsValidationTests.E` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:70-71` |
| `ParsableArgumentsValidationTests.E` | `count` | `Int?` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:73-74` |
| `ParsableArgumentsValidationTests.E` | `includeCounter` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:76-77` |
| `ParsableArgumentsValidationTests.TypeWithInvalidDecoder` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:121-122` |
| `ParsableArgumentsValidationTests.TypeWithInvalidDecoder` | `count` | `Int` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:124-125` |
| `ParsableArgumentsValidationTests.AsyncCompletionOptionGroup` | `option` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:163-168` |
| `ParsableArgumentsValidationTests.AsyncCompletionOptionGroup` | `arg` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:169-170` |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | `option` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:175-180` |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | `arg` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:181-185` |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | `og` | `AsyncCompletionOptionGroup` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:186-187` |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | `option` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:212-217` |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | `arg` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:218-222` |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | `og` | `AsyncCompletionOptionGroup` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:223-224` |
| `ParsableArgumentsValidationTests.TypeWithValidSyncCompletions` | `option` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:239-244` |
| `ParsableArgumentsValidationTests.TypeWithValidSyncCompletions` | `arg` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:245-249` |
| `ParsableArgumentsValidationTests.F` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:263-264` |
| `ParsableArgumentsValidationTests.F` | `items` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:266-267` |
| `ParsableArgumentsValidationTests.G` | `items` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:271-272` |
| `ParsableArgumentsValidationTests.G` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:274-275` |
| `ParsableArgumentsValidationTests.H` | `items` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:279-280` |
| `ParsableArgumentsValidationTests.H` | `option` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:282-283` |
| `ParsableArgumentsValidationTests.I` | `name` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:287-288` |
| `ParsableArgumentsValidationTests.I` | `options` | `F` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:290-291` |
| `ParsableArgumentsValidationTests.J.Options` | `numberOfItems` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:296-297` |
| `ParsableArgumentsValidationTests.J` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:300-301` |
| `ParsableArgumentsValidationTests.J` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:303-304` |
| `ParsableArgumentsValidationTests.K.Options` | `items` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:309-310` |
| `ParsableArgumentsValidationTests.K` | `phrase` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:313-314` |
| `ParsableArgumentsValidationTests.K` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:316-317` |
| `ParsableArgumentsValidationTests.L.Options` | `items` | `[Int]` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:323-323` |
| `ParsableArgumentsValidationTests.L` | `foo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:326-326` |
| `ParsableArgumentsValidationTests.L` | `bar` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:327-327` |
| `ParsableArgumentsValidationTests.L` | `options` | `Options` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:328-328` |
| `ParsableArgumentsValidationTests.L` | `flag` | — | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:329-329` |
| `ParsableArgumentsValidationTests` | `unexpectedErrorMessage` | — | fileprivate | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:365-365` |
| `ParsableArgumentsValidationTests.DifferentNames` | `foo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:370-371` |
| `ParsableArgumentsValidationTests.DifferentNames` | `bar` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:373-374` |
| `ParsableArgumentsValidationTests.TwoOfTheSameName` | `foo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:386-387` |
| `ParsableArgumentsValidationTests.TwoOfTheSameName` | `notActuallyFoo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:389-390` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | `foo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:408-409` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | `notActuallyFoo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:411-412` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | `bar` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:414-415` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | `notBar` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:417-418` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | `help` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:420-421` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument` | `verbose` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:448-449` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument` | `versimilitude` | `Versimilitude` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:457-458` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | `foo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:476-477` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | `notActuallyFoo` | `String` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:479-480` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | `stillNotFoo` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:482-483` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | `alsoNotFoo` | `Numbers` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:491-492` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames` | `enumFlag` | `ExampleEnum` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:523-524` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames` | `enumFlag2` | `ExampleEnum` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:536-537` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `enumFlag` | `ExampleEnum` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:571-572` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `fine` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:574-575` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `alsoFine` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:577-578` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `stillFine` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:580-581` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `yetStillFine` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:583-584` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | `nonsense` | `Bool` | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:586-587` |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | `stuff` | — | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:611-612` |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | `nonsense` | — | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:614-615` |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | `okay` | — | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:617-618` |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | `moreNonsense` | — | internal | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:620-621` |
| `SendableTests.Foo` | `foo` | `Bool` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:37-38` |
| `SendableTests.Foo` | `custom` | `MyExpressibleType?` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:40-41` |
| `SendableTests.Foo` | `transformed1` | `SendableClassType` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:43-44` |
| `SendableTests.Foo` | `transformed2` | `SendableClassType` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:46-47` |
| `SendableTests.Foo` | `arg` | `[MyExpressibleType]` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:49-50` |
| `SendableTests.Bar` | `foo` | `Foo` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:54-55` |
| `SendableTests.Baz` | `bar` | `Foo` | internal | `Tests/ArgumentParserUnitTests/SendableTests.swift:59-60` |
| `TreeTests.A` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:59-59` |
| `TreeTests.Root` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:62-62` |
| `TreeTests.Sub` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:65-65` |
| `TreeTests.RootWithNamedNestedSub` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:69-69` |
| `TreeTests.RootWithNamedNestedSub.NestedSub` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:74-74` |
| `TreeTests.RootWithNestedSub` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:80-80` |
| `TreeTests.RootWithNestedSub.NestedSub` | `configuration` | — | internal | `Tests/ArgumentParserUnitTests/TreeTests.swift:85-85` |
| `ChangelogAuthors` | `startingTag` | `String` | internal | `Tools/changelog-authors/ChangelogAuthors.swift:32-33` |
| `ChangelogAuthors` | `endingTag` | `String?` | internal | `Tools/changelog-authors/ChangelogAuthors.swift:35-36` |
| `ChangelogAuthors` | `repository` | `String` | internal | `Tools/changelog-authors/ChangelogAuthors.swift:38-41` |
| `Comparison` | `commits` | `[Commit]` | internal | `Tools/changelog-authors/Models.swift:15-15` |
| `Commit` | `sha` | `String` | internal | `Tools/changelog-authors/Models.swift:19-19` |
| `Commit` | `author` | `Author?` | internal | `Tools/changelog-authors/Models.swift:20-20` |
| `Author` | `login` | `String` | internal | `Tools/changelog-authors/Models.swift:24-24` |
| `Author` | `htmlURL` | `String` | internal | `Tools/changelog-authors/Models.swift:25-25` |
| `GenerateDoccReference` | `configuration` | — | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:49-49` |
| `GenerateDoccReference` | `tool` | `String` | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:53-54` |
| `GenerateDoccReference` | `outputDirectory` | `String` | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:56-59` |
| `GenerateDoccReference` | `style` | `OutputStyle` | internal | `Tools/generate-docc-reference/GenerateDoccReference.swift:61-64` |
| `Character` | `emailStart` | `Character` | fileprivate | `Tools/generate-manual/AuthorArgument.swift:16-16` |
| `Character` | `emailEnd` | `Character` | fileprivate | `Tools/generate-manual/AuthorArgument.swift:17-17` |
| `ArgumentSynopsis` | `argument` | `ArgumentInfoV0` | internal | `Tools/generate-manual/DSL/ArgumentSynopsis.swift:16-16` |
| `Author` | `author` | `AuthorArgument` | internal | `Tools/generate-manual/DSL/Author.swift:16-16` |
| `Author` | `trailing` | `String` | internal | `Tools/generate-manual/DSL/Author.swift:17-17` |
| `Authors` | `authors` | `[AuthorArgument]` | internal | `Tools/generate-manual/DSL/Authors.swift:16-16` |
| `Container` | `children` | `[MDocComponent]` | internal | `Tools/generate-manual/DSL/Core/Container.swift:18-18` |
| `ForEach` | `items` | `C` | internal | `Tools/generate-manual/DSL/Core/ForEach.swift:13-13` |
| `ForEach` | `builder` | `(C.Element, C.Index) -> MDocComponent` | internal | `Tools/generate-manual/DSL/Core/ForEach.swift:14-14` |
| `MDocASTNodeWrapper` | `node` | `MDocASTNode` | internal | `Tools/generate-manual/DSL/Core/MDocASTNodeWrapper.swift:15-15` |
| `DiscussionText` | `discussion` | `String?` | internal | `Tools/generate-manual/DSL/Discussion.swift:15-15` |
| `DiscussionText` | `allValueStrings` | `[String]?` | internal | `Tools/generate-manual/DSL/Discussion.swift:16-16` |
| `DiscussionText` | `allValueDescriptions` | `[String: String]?` | internal | `Tools/generate-manual/DSL/Discussion.swift:17-17` |
| `Document` | `multiPage` | `Bool` | internal | `Tools/generate-manual/DSL/Document.swift:17-17` |
| `Document` | `date` | `Date` | internal | `Tools/generate-manual/DSL/Document.swift:18-18` |
| `Document` | `section` | `Int` | internal | `Tools/generate-manual/DSL/Document.swift:19-19` |
| `Document` | `authors` | `[AuthorArgument]` | internal | `Tools/generate-manual/DSL/Document.swift:20-20` |
| `Document` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/Document.swift:21-21` |
| `DocumentDate` | `month` | `String` | private | `Tools/generate-manual/DSL/DocumentDate.swift:17-17` |
| `DocumentDate` | `day` | `Int` | private | `Tools/generate-manual/DSL/DocumentDate.swift:18-18` |
| `DocumentDate` | `year` | `Int` | private | `Tools/generate-manual/DSL/DocumentDate.swift:19-19` |
| `Exit` | `section` | `Int` | internal | `Tools/generate-manual/DSL/Exit.swift:16-16` |
| `List` | `content` | `MDocComponent` | internal | `Tools/generate-manual/DSL/List.swift:13-13` |
| `MultiPageDescription` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/MultiPageDescription.swift:16-16` |
| `Name` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/Name.swift:16-16` |
| `Preamble` | `date` | `Date` | internal | `Tools/generate-manual/DSL/Preamble.swift:17-17` |
| `Preamble` | `section` | `Int` | internal | `Tools/generate-manual/DSL/Preamble.swift:18-18` |
| `Preamble` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/Preamble.swift:19-19` |
| `Section` | `title` | `String` | internal | `Tools/generate-manual/DSL/Section.swift:13-13` |
| `Section` | `content` | `MDocComponent` | internal | `Tools/generate-manual/DSL/Section.swift:14-14` |
| `SeeAlso` | `section` | `Int` | internal | `Tools/generate-manual/DSL/SeeAlso.swift:16-16` |
| `SeeAlso` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/SeeAlso.swift:17-17` |
| `SinglePageDescription` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/SinglePageDescription.swift:16-16` |
| `SinglePageDescription` | `root` | `Bool` | internal | `Tools/generate-manual/DSL/SinglePageDescription.swift:17-17` |
| `SinglePageDescription` | `inheritedArguments` | `Set<ArgumentInfoV0>` | internal | `Tools/generate-manual/DSL/SinglePageDescription.swift:26-26` |
| `Synopsis` | `command` | `CommandInfoV0` | internal | `Tools/generate-manual/DSL/Synopsis.swift:16-16` |
| `GenerateManual` | `configuration` | — | internal | `Tools/generate-manual/GenerateManual.swift:41-41` |
| `GenerateManual` | `tool` | `String` | internal | `Tools/generate-manual/GenerateManual.swift:45-46` |
| `GenerateManual` | `multiPage` | — | internal | `Tools/generate-manual/GenerateManual.swift:48-49` |
| `GenerateManual` | `date` | `Date` | internal | `Tools/generate-manual/GenerateManual.swift:51-54` |
| `GenerateManual` | `section` | `Int` | internal | `Tools/generate-manual/GenerateManual.swift:56-57` |
| `GenerateManual` | `authors` | `[AuthorArgument]` | internal | `Tools/generate-manual/GenerateManual.swift:59-62` |
| `GenerateManual` | `outputDirectory` | `String` | internal | `Tools/generate-manual/GenerateManual.swift:64-67` |
| `MDocMacro.Comment` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:140-140` |
| `MDocMacro.Comment` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:141-141` |
| `MDocMacro.DocumentDate` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:161-161` |
| `MDocMacro.DocumentDate` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:162-162` |
| `MDocMacro.DocumentTitle` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:184-184` |
| `MDocMacro.DocumentTitle` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:185-185` |
| `MDocMacro.OperatingSystem` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:222-222` |
| `MDocMacro.OperatingSystem` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:223-223` |
| `MDocMacro.DocumentName` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:263-263` |
| `MDocMacro.DocumentName` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:264-264` |
| `MDocMacro.DocumentDescription` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:284-284` |
| `MDocMacro.DocumentDescription` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:285-285` |
| `MDocMacro.SectionHeader` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:310-310` |
| `MDocMacro.SectionHeader` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:311-311` |
| `MDocMacro.SubsectionHeader` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:332-332` |
| `MDocMacro.SubsectionHeader` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:333-333` |
| `MDocMacro.SectionReference` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:352-352` |
| `MDocMacro.SectionReference` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:353-353` |
| `MDocMacro.CrossManualReference` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:369-369` |
| `MDocMacro.CrossManualReference` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:370-370` |
| `MDocMacro.ParagraphBreak` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:387-387` |
| `MDocMacro.ParagraphBreak` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:388-388` |
| `MDocMacro.BeginList` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:484-484` |
| `MDocMacro.BeginList` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:485-485` |
| `MDocMacro.ListItem` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:537-537` |
| `MDocMacro.ListItem` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:538-538` |
| `MDocMacro.EndList` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:554-554` |
| `MDocMacro.EndList` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:555-555` |
| `MDocMacro.WithoutTrailingSpace` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:574-574` |
| `MDocMacro.WithoutTrailingSpace` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:575-575` |
| `MDocMacro.WithoutLeadingSpace` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:591-591` |
| `MDocMacro.WithoutLeadingSpace` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:592-592` |
| `MDocMacro.Apostrophe` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:608-608` |
| `MDocMacro.Apostrophe` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:609-609` |
| `MDocMacro.CommandOption` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:643-643` |
| `MDocMacro.CommandOption` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:644-644` |
| `MDocMacro.CommandModifier` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:666-666` |
| `MDocMacro.CommandModifier` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:667-667` |
| `MDocMacro.CommandArgument` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:691-691` |
| `MDocMacro.CommandArgument` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:692-692` |
| `MDocMacro.OptionalCommandLineComponent` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:714-714` |
| `MDocMacro.OptionalCommandLineComponent` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:715-715` |
| `MDocMacro.BeginOptionalCommandLineComponent` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:739-739` |
| `MDocMacro.BeginOptionalCommandLineComponent` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:740-740` |
| `MDocMacro.EndOptionalCommandLineComponent` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:749-749` |
| `MDocMacro.EndOptionalCommandLineComponent` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:750-750` |
| `MDocMacro.InteractiveCommand` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:771-771` |
| `MDocMacro.InteractiveCommand` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:772-772` |
| `MDocMacro.EnvironmentVariable` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:789-789` |
| `MDocMacro.EnvironmentVariable` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:790-790` |
| `MDocMacro.FilePath` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:808-808` |
| `MDocMacro.FilePath` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:809-809` |
| `MDocMacro.Author` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:880-880` |
| `MDocMacro.Author` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:881-881` |
| `MDocMacro.Hyperlink` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:905-905` |
| `MDocMacro.Hyperlink` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:906-906` |
| `MDocMacro.MailTo` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:925-925` |
| `MDocMacro.MailTo` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:926-926` |
| `MDocMacro.Emphasis` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:983-983` |
| `MDocMacro.Emphasis` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:984-984` |
| `MDocMacro.Boldface` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1006-1006` |
| `MDocMacro.Boldface` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1007-1007` |
| `MDocMacro.NormalText` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1024-1024` |
| `MDocMacro.NormalText` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1025-1025` |
| `MDocMacro.BeginFont` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1056-1056` |
| `MDocMacro.BeginFont` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1057-1057` |
| `MDocMacro.EndFont` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1075-1075` |
| `MDocMacro.EndFont` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1076-1076` |
| `MDocMacro.BeginTypographicDoubleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1096-1096` |
| `MDocMacro.BeginTypographicDoubleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1097-1097` |
| `MDocMacro.EndTypographicDoubleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1106-1106` |
| `MDocMacro.EndTypographicDoubleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1107-1107` |
| `MDocMacro.BeginTypewriterDoubleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1127-1127` |
| `MDocMacro.BeginTypewriterDoubleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1128-1128` |
| `MDocMacro.EndTypewriterDoubleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1137-1137` |
| `MDocMacro.EndTypewriterDoubleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1138-1138` |
| `MDocMacro.BeginSingleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1156-1156` |
| `MDocMacro.BeginSingleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1157-1157` |
| `MDocMacro.EndSingleQuotes` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1166-1166` |
| `MDocMacro.EndSingleQuotes` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1167-1167` |
| `MDocMacro.BeginParentheses` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1185-1185` |
| `MDocMacro.BeginParentheses` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1186-1186` |
| `MDocMacro.EndParentheses` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1195-1195` |
| `MDocMacro.EndParentheses` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1196-1196` |
| `MDocMacro.BeginSquareBrackets` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1214-1214` |
| `MDocMacro.BeginSquareBrackets` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1215-1215` |
| `MDocMacro.EndSquareBrackets` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1224-1224` |
| `MDocMacro.EndSquareBrackets` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1225-1225` |
| `MDocMacro.BeginCurlyBraces` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1243-1243` |
| `MDocMacro.BeginCurlyBraces` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1244-1244` |
| `MDocMacro.EndCurlyBraces` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1253-1253` |
| `MDocMacro.EndCurlyBraces` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1254-1254` |
| `MDocMacro.BeginAngleBrackets` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1272-1272` |
| `MDocMacro.BeginAngleBrackets` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1273-1273` |
| `MDocMacro.EndAngleBrackets` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1282-1282` |
| `MDocMacro.EndAngleBrackets` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1283-1283` |
| `MDocMacro.ExitStandard` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1304-1304` |
| `MDocMacro.ExitStandard` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1305-1305` |
| `MDocMacro.AttUnix` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1346-1346` |
| `MDocMacro.AttUnix` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1347-1347` |
| `MDocMacro.BSD` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1371-1371` |
| `MDocMacro.BSD` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1372-1372` |
| `MDocMacro.BSDOS` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1398-1398` |
| `MDocMacro.BSDOS` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1399-1399` |
| `MDocMacro.NetBSD` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1418-1418` |
| `MDocMacro.NetBSD` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1419-1419` |
| `MDocMacro.FreeBSD` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1438-1438` |
| `MDocMacro.FreeBSD` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1439-1439` |
| `MDocMacro.OpenBSD` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1458-1458` |
| `MDocMacro.OpenBSD` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1459-1459` |
| `MDocMacro.DragonFly` | `kind` | — | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1478-1478` |
| `MDocMacro.DragonFly` | `arguments` | `[MDocASTNode]` | public | `Tools/generate-manual/MDoc/MDocMacro.swift:1479-1479` |
| `MDocSerializationContext` | `macroLine` | `Bool` | internal | `Tools/generate-manual/MDoc/MDocSerializationContext.swift:14-14` |

## Relationships

| from type | relation | to type | declared at |
|---|---|---|---|
| `Color` | conforms | `ParsableCommand` | `Examples/color/Color.swift:14-15` |
| `Color` | stores | `ColorOptions` | `Examples/color/Color.swift:16-17` |
| `Color` | stores | `ColorOptions` | `Examples/color/Color.swift:19-21` |
| `ColorOptions` | conforms | `CaseIterable` | `Examples/color/Color.swift:31-31` |
| `ColorOptions` | conforms | `ExpressibleByArgument` | `Examples/color/Color.swift:31-31` |
| `ColorOptions` | conforms | `String` | `Examples/color/Color.swift:31-31` |
| `CountLines` | conforms | `AsyncParsableCommand` | `Examples/count-lines/CountLines.swift:15-17` |
| `DefaultAsFlag` | conforms | `ParsableCommand` | `Examples/default-as-flag/DefaultAsFlag.swift:14-15` |
| `Math` | conforms | `ParsableCommand` | `Examples/math/Math.swift:14-15` |
| `Options` | conforms | `ParsableArguments` | `Examples/math/Math.swift:36-36` |
| `Math.Add` | conforms | `ParsableCommand` | `Examples/math/Math.swift:54-54` |
| `Math.Add` | stores | `Options` | `Examples/math/Math.swift:60-60` |
| `Math.Multiply` | conforms | `ParsableCommand` | `Examples/math/Math.swift:68-68` |
| `Math.Multiply` | stores | `Options` | `Examples/math/Math.swift:73-73` |
| `Math.Statistics` | conforms | `ParsableCommand` | `Examples/math/Math.swift:84-84` |
| `Math.Statistics.Average` | conforms | `ParsableCommand` | `Examples/math/Math.swift:95-95` |
| `Math.Statistics.Average.Kind` | conforms | `CaseIterable` | `Examples/math/Math.swift:101-101` |
| `Math.Statistics.Average.Kind` | conforms | `ExpressibleByArgument` | `Examples/math/Math.swift:101-101` |
| `Math.Statistics.Average.Kind` | conforms | `String` | `Examples/math/Math.swift:101-101` |
| `Math.Statistics.Average` | stores | `Kind` | `Examples/math/Math.swift:105-106` |
| `Math.Statistics.StandardDeviation` | conforms | `ParsableCommand` | `Examples/math/Math.swift:167-167` |
| `Math.Statistics.Quantiles` | conforms | `ParsableCommand` | `Examples/math/Math.swift:192-192` |
| `Repeat` | conforms | `ParsableCommand` | `Examples/repeat/Repeat.swift:14-15` |
| `SplitMix64` | conforms | `RandomNumberGenerator` | `Examples/roll/SplitMix64.swift:12-12` |
| `RollOptions` | conforms | `ParsableArguments` | `Examples/roll/main.swift:14-14` |
| `GeneratePluginError` | conforms | `Error` | `Plugins/GenerateCommon/GeneratePluginError.swift:15-15` |
| `GeneratePluginError` | conforms (extension) | `CustomStringConvertible` | `Plugins/GenerateCommon/GeneratePluginError.swift:23-23` |
| `GeneratePluginError` | conforms (extension) | `LocalizedError` | `Plugins/GenerateCommon/GeneratePluginError.swift:48-48` |
| `GenerateDoccReferencePlugin` | conforms | `GeneratePlugin` | `Plugins/GenerateDoccReference/GenerateDoccReference.swift:15-16` |
| `GenerateManualPlugin` | conforms | `GeneratePlugin` | `Plugins/GenerateManual/GenerateManualPlugin.swift:15-16` |
| `CompletionShell` | conforms | `CaseIterable` | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:15-15` |
| `CompletionShell` | conforms | `Hashable` | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:15-15` |
| `CompletionShell` | conforms | `RawRepresentable` | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:15-15` |
| `CompletionShell` | conforms | `Sendable` | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:15-15` |
| `CompletionsGenerator` | stores | `CompletionShell` | `Sources/ArgumentParser/Completions/CompletionsGenerator.swift:99-99` |
| `Argument` | conforms | `Decodable` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:44-45` |
| `Argument` | conforms | `ParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:44-45` |
| `Argument` | stores | `Parsed` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:48-48` |
| `Argument` | stores | `Value` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:48-48` |
| `Argument` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:94-94` |
| `Argument` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:105-105` |
| `Argument` | conforms (extension) | `DecodableParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:106-106` |
| `ArgumentArrayParsingStrategy` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:110-110` |
| `ArgumentArrayParsingStrategy` | stores | `ArgumentDefinition` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:111-111` |
| `ArgumentArrayParsingStrategy` | stores | `ParsingStrategy` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:111-111` |
| `ArgumentArrayParsingStrategy` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Argument.swift:313-313` |
| `ArgumentDiscussion` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/ArgumentDiscussion.swift:138-138` |
| `ArgumentDiscussion` | conforms (extension) | `Hashable` | `Sources/ArgumentParser/Parsable Properties/ArgumentDiscussion.swift:140-140` |
| `ArgumentHelp` | stores | `ArgumentVisibility` | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:29-29` |
| `ArgumentHelp` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:90-90` |
| `ArgumentHelp` | conforms (extension) | `ExpressibleByStringInterpolation` | `Sources/ArgumentParser/Parsable Properties/ArgumentHelp.swift:92-92` |
| `ArgumentVisibility` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:13-13` |
| `ArgumentVisibility` | stores | `Representation` | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:22-22` |
| `ArgumentVisibility` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/ArgumentVisibility.swift:34-34` |
| `CompletionKind` | stores | `Kind` | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:48-48` |
| `CompletionKind` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:209-209` |
| `CompletionKind.Kind` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/CompletionKind.swift:210-210` |
| `ValidationError` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:14-14` |
| `ValidationError` | conforms | `Error` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:14-14` |
| `ExitCode` | conforms | `Error` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:35-35` |
| `ExitCode` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:35-35` |
| `ExitCode` | conforms | `RawRepresentable` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:35-35` |
| `CleanExit` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:70-70` |
| `CleanExit` | conforms | `Error` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:70-70` |
| `CleanExit` | stores | `Representation` | `Sources/ArgumentParser/Parsable Properties/Errors.swift:77-77` |
| `Flag` | conforms | `Decodable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:71-72` |
| `Flag` | conforms | `ParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:71-72` |
| `Flag` | stores | `Parsed` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:73-73` |
| `Flag` | stores | `Value` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:73-73` |
| `Flag` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:119-119` |
| `Flag` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:121-121` |
| `Flag` | conforms (extension) | `DecodableParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:132-132` |
| `FlagInversion` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:135-135` |
| `FlagInversion` | stores | `Representation` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:141-141` |
| `FlagInversion` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:169-169` |
| `FlagExclusivity` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:172-172` |
| `FlagExclusivity` | stores | `Representation` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:179-179` |
| `FlagExclusivity` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Flag.swift:197-197` |
| `NameSpecification` | conforms | `ExpressibleByArrayLiteral` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:33-33` |
| `NameSpecification.Element` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:35-35` |
| `NameSpecification.Element` | conforms | `Sendable` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:35-35` |
| `NameSpecification.Element.Representation` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:36-36` |
| `NameSpecification.Element` | stores | `Representation` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:44-44` |
| `NameSpecification` | stores | `Element` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:111-111` |
| `NameSpecification` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:122-122` |
| `NameSpecification.Element` | conforms (extension) | `ExpressibleByStringInterpolation` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:124-124` |
| `NameSpecification.Element` | conforms (extension) | `ExpressibleByStringLiteral` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:124-124` |
| `NameSpecification` | conforms (extension) | `ExpressibleByStringInterpolation` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:169-169` |
| `NameSpecification` | conforms (extension) | `ExpressibleByStringLiteral` | `Sources/ArgumentParser/Parsable Properties/NameSpecification.swift:169-169` |
| `Option` | conforms | `Decodable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:51-52` |
| `Option` | conforms | `ParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Option.swift:51-52` |
| `Option` | stores | `Parsed` | `Sources/ArgumentParser/Parsable Properties/Option.swift:53-53` |
| `Option` | stores | `Value` | `Sources/ArgumentParser/Parsable Properties/Option.swift:53-53` |
| `Option` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/Option.swift:99-99` |
| `Option` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:110-110` |
| `Option` | conforms (extension) | `DecodableParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/Option.swift:111-111` |
| `SingleValueParsingStrategy` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:116-116` |
| `SingleValueParsingStrategy` | stores | `ArgumentDefinition` | `Sources/ArgumentParser/Parsable Properties/Option.swift:117-117` |
| `SingleValueParsingStrategy` | stores | `ParsingStrategy` | `Sources/ArgumentParser/Parsable Properties/Option.swift:117-117` |
| `DefaultAsFlagParsingStrategy` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:168-168` |
| `DefaultAsFlagParsingStrategy` | stores | `ArgumentDefinition` | `Sources/ArgumentParser/Parsable Properties/Option.swift:169-169` |
| `DefaultAsFlagParsingStrategy` | stores | `ParsingStrategy` | `Sources/ArgumentParser/Parsable Properties/Option.swift:169-169` |
| `SingleValueParsingStrategy` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:202-202` |
| `DefaultAsFlagParsingStrategy` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:203-203` |
| `ArrayParsingStrategy` | conforms | `Hashable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:207-207` |
| `ArrayParsingStrategy` | stores | `ArgumentDefinition` | `Sources/ArgumentParser/Parsable Properties/Option.swift:208-208` |
| `ArrayParsingStrategy` | stores | `ParsingStrategy` | `Sources/ArgumentParser/Parsable Properties/Option.swift:208-208` |
| `ArrayParsingStrategy` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/Option.swift:285-285` |
| `OptionGroup` | conforms | `Decodable` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:33-34` |
| `OptionGroup` | conforms | `ParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:33-34` |
| `OptionGroup` | stores | `Parsed` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:35-35` |
| `OptionGroup` | stores | `Value` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:35-35` |
| `OptionGroup` | stores | `ArgumentVisibility` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:36-36` |
| `OptionGroup` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:116-116` |
| `OptionGroup` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/OptionGroup.swift:118-118` |
| `ParentCommand` | conforms | `Decodable` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:42-43` |
| `ParentCommand` | conforms | `ParsedWrapper` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:42-43` |
| `ParentCommand` | stores | `Parsed` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:44-44` |
| `ParentCommand` | stores | `Value` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:44-44` |
| `ParentCommand` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:83-83` |
| `ParentCommand` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsable Properties/ParentCommand.swift:85-85` |
| `CommandConfiguration` | conforms | `Sendable` | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:13-13` |
| `CommandConfiguration` | stores | `CommandGroup` | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:82-82` |
| `CommandConfiguration` | stores | `NameSpecification` | `Sources/ArgumentParser/Parsable Types/CommandConfiguration.swift:88-88` |
| `CommandGroup` | conforms | `Sendable` | `Sources/ArgumentParser/Parsable Types/CommandGroup.swift:13-13` |
| `String` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:100-100` |
| `Int` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:136-136` |
| `Int8` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:137-137` |
| `Int16` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:138-138` |
| `Int32` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:139-139` |
| `Int64` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:140-140` |
| `UInt` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:141-141` |
| `UInt8` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:142-142` |
| `UInt16` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:143-143` |
| `UInt32` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:144-144` |
| `UInt64` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:145-145` |
| `Float` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:147-147` |
| `Double` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:148-148` |
| `Bool` | conforms (extension) | `ExpressibleByArgument` | `Sources/ArgumentParser/Parsable Types/ExpressibleByArgument.swift:150-150` |
| `_WrappedParsableCommand` | conforms | `ParsableCommand` | `Sources/ArgumentParser/Parsable Types/ParsableArguments.swift:40-40` |
| `_WrappedParsableCommand` | stores | `P` | `Sources/ArgumentParser/Parsable Types/ParsableArguments.swift:56-56` |
| `ArgumentDecoder` | conforms | `Decoder` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:31-31` |
| `ArgumentDecoder` | stores | `ParsedValues` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:38-38` |
| `ArgumentDecoder` | stores | `InputOrigin` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:39-39` |
| `ArgumentDecoder` | stores | `DecodedArguments` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:41-41` |
| `ArgumentDecoder.Error` | conforms | `Swift.Error` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:72-72` |
| `ParsedArgumentsContainer` | conforms | `KeyedDecodingContainerProtocol` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:80-80` |
| `ParsedArgumentsContainer` | stores | `ArgumentDecoder` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:84-84` |
| `SingleValueDecoder` | conforms | `Decoder` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:173-173` |
| `SingleValueDecoder` | stores | `ArgumentDecoder` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:175-175` |
| `SingleValueDecoder` | stores | `InputKey` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:177-177` |
| `SingleValueDecoder` | stores | `Element` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:178-178` |
| `SingleValueDecoder` | stores | `ParsedValues` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:178-178` |
| `SingleValueDecoder.SingleValueContainer` | conforms | `SingleValueDecodingContainer` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:224-224` |
| `SingleValueDecoder.SingleValueContainer` | stores | `SingleValueDecoder` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:225-225` |
| `SingleValueDecoder.SingleValueContainer` | stores | `Element` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:227-227` |
| `SingleValueDecoder.SingleValueContainer` | stores | `ParsedValues` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:227-227` |
| `SingleValueDecoder.UnkeyedContainer` | conforms | `UnkeyedDecodingContainer` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:250-250` |
| `SingleValueDecoder.UnkeyedContainer` | stores | `Element` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:252-252` |
| `SingleValueDecoder.UnkeyedContainer` | stores | `ParsedValues` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:252-252` |
| `ArrayWrapper` | conforms | `ArrayWrapperProtocol` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:304-304` |
| `ArrayWrapper` | stores | `A` | `Sources/ArgumentParser/Parsing/ArgumentDecoder.swift:305-305` |
| `ArgumentDefinition.Help.Options` | conforms | `OptionSet` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:46-46` |
| `ArgumentDefinition.Help` | stores | `Options` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:53-53` |
| `ArgumentDefinition.Help` | stores | `InputKey` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:55-55` |
| `ArgumentDefinition.Help` | stores | `ArgumentDiscussion` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:59-59` |
| `ArgumentDefinition.Help` | stores | `ArgumentVisibility` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:61-61` |
| `ArgumentDefinition` | stores | `Kind` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:107-107` |
| `ArgumentDefinition` | stores | `Help` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:108-108` |
| `ArgumentDefinition` | stores | `CompletionKind` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:109-109` |
| `ArgumentDefinition` | stores | `ParsingStrategy` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:110-110` |
| `ArgumentDefinition` | stores | `Update` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:111-111` |
| `ArgumentDefinition` | conforms (extension) | `CustomDebugStringConvertible` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:153-153` |
| `Bare` | conforms (extension) | `ArgumentDefinitionContainer` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:383-383` |
| `Bare` | conforms (extension) | `ArgumentDefinitionContainerExpressibleByArgument` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:399-399` |
| `Optional` | conforms (extension) | `ArgumentDefinitionContainer` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:412-412` |
| `Optional` | conforms (extension) | `ArgumentDefinitionContainerExpressibleByArgument` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:428-428` |
| `Array` | conforms (extension) | `ArgumentDefinitionContainer` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:439-439` |
| `Array` | conforms (extension) | `ArgumentDefinitionContainerExpressibleByArgument` | `Sources/ArgumentParser/Parsing/ArgumentDefinition.swift:459-459` |
| `ArgumentSet` | stores | `ArgumentDefinition` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:22-22` |
| `ArgumentSet` | stores | `Name` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:23-23` |
| `ArgumentSet` | conforms (extension) | `CustomDebugStringConvertible` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:53-53` |
| `ArgumentSet` | conforms (extension) | `RandomAccessCollection` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:61-61` |
| `LenientParser` | stores | `ArgumentSet` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:257-257` |
| `LenientParser` | stores | `SplitArguments` | `Sources/ArgumentParser/Parsing/ArgumentSet.swift:258-258` |
| `CommandError` | conforms | `Error` | `Sources/ArgumentParser/Parsing/CommandParser.swift:12-12` |
| `CommandError` | stores | `ParserError` | `Sources/ArgumentParser/Parsing/CommandParser.swift:14-14` |
| `HelpRequested` | conforms | `Error` | `Sources/ArgumentParser/Parsing/CommandParser.swift:17-17` |
| `HelpRequested` | stores | `ArgumentVisibility` | `Sources/ArgumentParser/Parsing/CommandParser.swift:18-18` |
| `CommandParser` | stores | `Tree` | `Sources/ArgumentParser/Parsing/CommandParser.swift:22-22` |
| `CommandParser` | stores | `Tree` | `Sources/ArgumentParser/Parsing/CommandParser.swift:23-23` |
| `CommandParser` | stores | `DecodedArguments` | `Sources/ArgumentParser/Parsing/CommandParser.swift:24-24` |
| `GenerateCompletions` | conforms | `ParsableCommand` | `Sources/ArgumentParser/Parsing/CommandParser.swift:435-435` |
| `AutodetectedGenerateCompletions` | conforms | `ParsableCommand` | `Sources/ArgumentParser/Parsing/CommandParser.swift:439-439` |
| `InputKey` | conforms | `Hashable` | `Sources/ArgumentParser/Parsing/InputKey.swift:18-18` |
| `InputKey` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsing/InputKey.swift:56-56` |
| `InputOrigin` | conforms | `Equatable` | `Sources/ArgumentParser/Parsing/InputOrigin.swift:30-30` |
| `InputOrigin` | conforms | `ExpressibleByArrayLiteral` | `Sources/ArgumentParser/Parsing/InputOrigin.swift:30-30` |
| `InputOrigin.Element` | conforms | `Comparable` | `Sources/ArgumentParser/Parsing/InputOrigin.swift:31-31` |
| `InputOrigin.Element` | conforms | `Hashable` | `Sources/ArgumentParser/Parsing/InputOrigin.swift:31-31` |
| `InputOrigin` | stores | `Element` | `Sources/ArgumentParser/Parsing/InputOrigin.swift:61-61` |
| `Name` | conforms (extension) | `Comparable` | `Sources/ArgumentParser/Parsing/Name.swift:41-41` |
| `Name` | conforms (extension) | `Hashable` | `Sources/ArgumentParser/Parsing/Name.swift:47-47` |
| `Name.Case` | conforms | `Equatable` | `Sources/ArgumentParser/Parsing/Name.swift:50-50` |
| `Parsed` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Parsing/Parsed.swift:32-32` |
| `ParsedValues.Element` | stores | `InputKey` | `Sources/ArgumentParser/Parsing/ParsedValues.swift:17-17` |
| `ParsedValues.Element` | stores | `InputOrigin` | `Sources/ArgumentParser/Parsing/ParsedValues.swift:20-20` |
| `ParsedValues` | stores | `Element` | `Sources/ArgumentParser/Parsing/ParsedValues.swift:25-25` |
| `ParsedValues` | stores | `InputKey` | `Sources/ArgumentParser/Parsing/ParsedValues.swift:25-25` |
| `ParserError` | conforms | `Error` | `Sources/ArgumentParser/Parsing/ParserError.swift:13-13` |
| `InternalParseError` | conforms | `Error` | `Sources/ArgumentParser/Parsing/ParserError.swift:45-45` |
| `ParsedArgument` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:15-15` |
| `ParsedArgument` | conforms | `Equatable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:15-15` |
| `SplitArguments.Element` | conforms | `Equatable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:90-90` |
| `SplitArguments.Element.Value` | conforms | `Equatable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:91-91` |
| `SplitArguments.Element` | stores | `Value` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:107-107` |
| `SplitArguments.Element` | stores | `Index` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:108-108` |
| `SplitArguments.InputIndex` | conforms | `Comparable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:127-127` |
| `SplitArguments.InputIndex` | conforms | `Hashable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:127-127` |
| `SplitArguments.InputIndex` | conforms | `RawRepresentable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:127-127` |
| `SplitArguments.SubIndex` | conforms | `Comparable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:144-144` |
| `SplitArguments.SubIndex` | conforms | `Hashable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:144-144` |
| `SplitArguments.Index` | conforms | `Comparable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:161-161` |
| `SplitArguments.Index` | conforms | `Hashable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:161-161` |
| `SplitArguments.Index` | stores | `InputIndex` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:173-173` |
| `SplitArguments.Index` | stores | `SubIndex` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:174-174` |
| `SplitArguments` | stores | `Element` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:182-182` |
| `SplitArguments` | conforms (extension) | `Equatable` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:198-198` |
| `SplitArguments.Element` | conforms (extension) | `CustomDebugStringConvertible` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:200-200` |
| `SplitArguments.Index` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:215-215` |
| `SplitArguments` | conforms (extension) | `CustomStringConvertible` | `Sources/ArgumentParser/Parsing/SplitArguments.swift:224-224` |
| `DumpHelpGenerator` | stores | `ToolInfoV0` | `Sources/ArgumentParser/Usage/DumpHelpGenerator.swift:15-15` |
| `HelpCommand` | conforms | `ParsableCommand` | `Sources/ArgumentParser/Usage/HelpCommand.swift:12-12` |
| `HelpCommand` | stores | `ArgumentVisibility` | `Sources/ArgumentParser/Usage/HelpCommand.swift:28-28` |
| `HelpCommand.CodingKeys` | conforms | `CodingKey` | `Sources/ArgumentParser/Usage/HelpCommand.swift:51-51` |
| `HelpGenerator.Section.Element` | conforms | `Hashable` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:18-18` |
| `HelpGenerator.Section.Element` | stores | `ArgumentDiscussion` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:21-21` |
| `HelpGenerator.Section.Header` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:108-108` |
| `HelpGenerator.Section.Header` | conforms | `Equatable` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:108-108` |
| `HelpGenerator.Section` | stores | `Header` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:131-131` |
| `HelpGenerator.Section` | stores | `Element` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:132-132` |
| `HelpGenerator` | stores | `Section` | `Sources/ArgumentParser/Usage/HelpGenerator.swift:155-155` |
| `UsageGenerator` | stores | `ArgumentSet` | `Sources/ArgumentParser/Usage/UsageGenerator.swift:14-14` |
| `ErrorMessageGenerator` | stores | `ArgumentSet` | `Sources/ArgumentParser/Usage/UsageGenerator.swift:175-175` |
| `ErrorMessageGenerator` | stores | `ParserError` | `Sources/ArgumentParser/Usage/UsageGenerator.swift:176-176` |
| `Mutex._Buffer` | conforms | `ManagedBuffer<State, _Lock.Primitive>` | `Sources/ArgumentParser/Utilities/Mutex.swift:96-96` |
| `Mutex` | stores | `_Lock` | `Sources/ArgumentParser/Utilities/Mutex.swift:104-104` |
| `Mutex` | conforms (extension) | `Sendable` | `Sources/ArgumentParser/Utilities/Mutex.swift:143-143` |
| `Platform.StandardError` | conforms | `TextOutputStream` | `Sources/ArgumentParser/Utilities/Platform.swift:191-191` |
| `Tree` | stores | `Element` | `Sources/ArgumentParser/Utilities/Tree.swift:13-13` |
| `Tree` | stores | `Tree` | `Sources/ArgumentParser/Utilities/Tree.swift:14-14` |
| `Tree` | stores | `Tree` | `Sources/ArgumentParser/Utilities/Tree.swift:15-15` |
| `Tree` | conforms (extension) | `Hashable` | `Sources/ArgumentParser/Utilities/Tree.swift:33-33` |
| `Tree.InitializationError` | conforms | `Error` | `Sources/ArgumentParser/Utilities/Tree.swift:108-108` |
| `AsyncCompletionsValidator` | conforms | `ParsableArgumentsValidator` | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:14-15` |
| `AsyncCompletionsValidator.Error` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:16-16` |
| `AsyncCompletionsValidator.Error` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:16-16` |
| `OptionGroup` | conforms (extension) | `AnyOptionGroup` | `Sources/ArgumentParser/Validators/AsyncCompletionsValidator.swift:59-59` |
| `CodingKeyValidator` | conforms | `ParsableArgumentsValidator` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:13-13` |
| `CodingKeyValidator.Validator` | conforms | `Decoder` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:14-14` |
| `CodingKeyValidator.Validator` | stores | `InputKey` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:15-15` |
| `CodingKeyValidator.Validator.ValidationResult` | conforms | `Swift.Error` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:17-17` |
| `CodingKeyValidator.MissingKeysError` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:47-47` |
| `CodingKeyValidator.MissingKeysError` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:47-47` |
| `CodingKeyValidator.MissingKeysError` | stores | `InputKey` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:50-50` |
| `CodingKeyValidator.InvalidDecoderError` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:80-80` |
| `CodingKeyValidator.InvalidDecoderError` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/CodingKeyValidator.swift:80-80` |
| `NonsenseFlagsValidator` | conforms | `ParsableArgumentsValidator` | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:13-13` |
| `NonsenseFlagsValidator.Error` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:14-14` |
| `NonsenseFlagsValidator.Error` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/NonsenseFlagsValidator.swift:14-14` |
| `ParsableArgumentsValidationError` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:53-53` |
| `ParsableArgumentsValidationError` | conforms | `Error` | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:53-53` |
| `ParsableArgumentsValidationError` | stores | `Error` | `Sources/ArgumentParser/Validators/ParsableArgumentsValidation.swift:55-55` |
| `PositionalArgumentsValidator` | conforms | `ParsableArgumentsValidator` | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:18-18` |
| `PositionalArgumentsValidator.Error` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:19-19` |
| `PositionalArgumentsValidator.Error` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/PositionalArgumentsValidator.swift:19-19` |
| `UniqueNamesValidator` | conforms | `ParsableArgumentsValidator` | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:14-14` |
| `UniqueNamesValidator.Error` | conforms | `CustomStringConvertible` | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:15-15` |
| `UniqueNamesValidator.Error` | conforms | `ParsableArgumentsValidatorError` | `Sources/ArgumentParser/Validators/UniqueNamesValidator.swift:15-15` |
| `CollectionDifference.Change` | conforms (extension) | `Swift.Comparable` | `Sources/ArgumentParserTestHelpers/TestHelpers.swift:28-29` |
| `ToolInfoHeader` | conforms | `Decodable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:18-18` |
| `ToolInfoV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:30-30` |
| `ToolInfoV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:30-30` |
| `ToolInfoV0` | stores | `CommandInfoV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:35-35` |
| `CommandInfoV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:44-44` |
| `CommandInfoV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:44-44` |
| `CommandInfoV0` | stores | `CommandInfoV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:63-63` |
| `CommandInfoV0` | stores | `ArgumentInfoV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:65-65` |
| `ArgumentInfoV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:115-115` |
| `ArgumentInfoV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:115-115` |
| `ArgumentInfoV0.NameInfoV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:117-117` |
| `ArgumentInfoV0.NameInfoV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:117-117` |
| `ArgumentInfoV0.NameInfoV0.KindV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:119-119` |
| `ArgumentInfoV0.NameInfoV0.KindV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:119-119` |
| `ArgumentInfoV0.NameInfoV0.KindV0` | conforms | `String` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:119-119` |
| `ArgumentInfoV0.NameInfoV0` | stores | `KindV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:129-129` |
| `ArgumentInfoV0.KindV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:140-140` |
| `ArgumentInfoV0.KindV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:140-140` |
| `ArgumentInfoV0.KindV0` | conforms | `String` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:140-140` |
| `ArgumentInfoV0.ParsingStrategyV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:149-149` |
| `ArgumentInfoV0.ParsingStrategyV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:149-149` |
| `ArgumentInfoV0.ParsingStrategyV0` | conforms | `String` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:149-149` |
| `ArgumentInfoV0.CompletionKindV0` | conforms | `Codable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:169-169` |
| `ArgumentInfoV0.CompletionKindV0` | conforms | `Hashable` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:169-169` |
| `ArgumentInfoV0` | stores | `KindV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:188-188` |
| `ArgumentInfoV0` | stores | `ParsingStrategyV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:201-201` |
| `ArgumentInfoV0` | stores | `NameInfoV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:204-204` |
| `ArgumentInfoV0` | stores | `NameInfoV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:206-206` |
| `ArgumentInfoV0` | stores | `CompletionKindV0` | `Sources/ArgumentParserToolInfo/ToolInfo.swift:229-229` |
| `AsyncStatusCheck.Status` | conforms | `OptionSet` | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:18-18` |
| `AsyncStatusCheck` | stores | `Status` | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:25-26` |
| `AsyncCommand` | conforms | `AsyncParsableCommand` | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:39-39` |
| `AsyncCommand.SubCommand` | conforms | `AsyncParsableCommand` | `Tests/ArgumentParserEndToEndTests/AsyncCommandEndToEndTests.swift:48-48` |
| `Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:41-41` |
| `Foo.Subgroup` | conforms | `Equatable` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:42-42` |
| `Foo.Subgroup` | conforms | `Sendable` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:42-42` |
| `Foo` | stores | `Subgroup` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:63-64` |
| `Foo` | stores | `Subgroup` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:66-67` |
| `Bar` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:100-100` |
| `Bar` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:101-103` |
| `Bar` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:105-106` |
| `Qux` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:148-148` |
| `Qux` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:149-150` |
| `Qux` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/CustomParsingEndToEndTests.swift:152-153` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformExplicitNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:21-21` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithoutTransformNoExplicitNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:29-29` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformExplicitNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:37-37` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagWithTransformNoExplicitNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:47-47` |
| `DefaultAsFlagEndToEndTests.CommandWithDefaultAsFlagAndArguments` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift:150-150` |
| `Main` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:22-22` |
| `Default` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:29-29` |
| `Default.Mode` | conforms | `CaseIterable` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:30-30` |
| `Default.Mode` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:30-30` |
| `Default.Mode` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:30-30` |
| `Default` | stores | `Mode` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:34-34` |
| `Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:37-37` |
| `Bar` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:38-38` |
| `DefaultSubcommandEndToEndTests.MyCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:78-78` |
| `DefaultSubcommandEndToEndTests.MyCommand` | stores | `CommonOptions` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:88-89` |
| `DefaultSubcommandEndToEndTests.CommonOptions` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:92-92` |
| `DefaultSubcommandEndToEndTests.Plugin` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:99-99` |
| `DefaultSubcommandEndToEndTests.Plugin` | stores | `CommonOptions` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:100-100` |
| `DefaultSubcommandEndToEndTests.NonDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:107-107` |
| `DefaultSubcommandEndToEndTests.NonDefault` | stores | `CommonOptions` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:108-108` |
| `DefaultSubcommandEndToEndTests.Other` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:115-115` |
| `DefaultSubcommandEndToEndTests.Other` | stores | `CommonOptions` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:116-116` |
| `DefaultSubcommandEndToEndTests.Child` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:119-119` |
| `DefaultSubcommandEndToEndTests.Child` | stores | `MyCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:120-120` |
| `DefaultSubcommandEndToEndTests.BadParent` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:123-123` |
| `DefaultSubcommandEndToEndTests.BadParent` | stores | `Other` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:124-124` |
| `DefaultSubcommandEndToEndTests.RootWithPassthroughDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:312-312` |
| `DefaultSubcommandEndToEndTests.PassthroughDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:320-320` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:340-340` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.Default` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:346-346` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.Nested` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:348-348` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.NestedDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:356-356` |
| `DefaultSubcommandEndToEndTests.NestedDefaultSubcommandHelp.NestedOther` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultSubcommandEndToEndTests.swift:357-357` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:20-20` |
| `Foo.Name` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:21-21` |
| `Foo.Name` | conforms | `RawRepresentable` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:21-21` |
| `Foo` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:24-25` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:57-57` |
| `Bar.Format` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:59-59` |
| `Bar.Format` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:59-59` |
| `Bar` | stores | `Format` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:66-67` |
| `Bar_NextInput` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:240-240` |
| `Bar_NextInput.Format` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:241-241` |
| `Bar_NextInput.Format` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:241-241` |
| `Bar_NextInput` | stores | `Format` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:249-250` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:300-300` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:404-404` |
| `OptionPropertyInitArguments_Default` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:446-446` |
| `OptionPropertyInitArguments_NoDefault_NoTransform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:454-454` |
| `OptionPropertyInitArguments_NoDefault_Transform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:461-461` |
| `ArgumentPropertyInitArguments_Default_NoTransform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:546-546` |
| `ArgumentPropertyInitArguments_NoDefault_NoTransform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:553-553` |
| `ArgumentPropertyInitArguments_Default_Transform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:560-560` |
| `ArgumentPropertyInitArguments_NoDefault_Transform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:567-567` |
| `Quux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:653-653` |
| `FlagPropertyInitArguments_Bool_Default` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:683-683` |
| `FlagPropertyInitArguments_Bool_NoDefault` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:688-688` |
| `HasData` | conforms | `EnumerableFlag` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:726-726` |
| `FlagPropertyInitArguments_EnumerableFlag_Default` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:731-731` |
| `FlagPropertyInitArguments_EnumerableFlag_Default` | stores | `HasData` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:734-735` |
| `FlagPropertyInitArguments_EnumerableFlag_NoDefault` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:738-738` |
| `FlagPropertyInitArguments_EnumerableFlag_NoDefault` | stores | `HasData` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:741-742` |
| `Main` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:785-785` |
| `Main.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:791-791` |
| `Main.Sub` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:796-796` |
| `Main.Sub` | stores | `Main` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:800-801` |
| `Main.Sub` | stores | `Options` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:800-801` |
| `RequiredArray_Option_NoTransform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:830-830` |
| `RequiredArray_Option_Transform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:835-835` |
| `RequiredArray_Argument_NoTransform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:840-840` |
| `RequiredArray_Argument_Transform` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:845-845` |
| `RequiredArray_Flag` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:850-850` |
| `RequiredArray_Flag` | stores | `HasData` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:851-852` |
| `OptionPropertyDeprecatedInit_NoDefault` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:981-982` |
| `DefaultsEndToEndTests.AbsolutePath` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1001-1001` |
| `DefaultsEndToEndTests.TwoPaths` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1006-1006` |
| `DefaultsEndToEndTests.UnderscoredOptional` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1036-1036` |
| `DefaultsEndToEndTests.UnderscoredArray` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/DefaultsEndToEndTests.swift:1041-1041` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:20-20` |
| `Bar.Index` | conforms | `Equatable` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:21-21` |
| `Bar.Index` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:21-21` |
| `Bar.Index` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:21-21` |
| `Bar` | stores | `Index` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:26-27` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:57-57` |
| `Baz.Mode` | conforms | `CaseIterable` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:58-58` |
| `Baz.Mode` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:58-58` |
| `Baz.Mode` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:58-58` |
| `Baz` | stores | `Mode` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:63-63` |
| `Baz` | stores | `Mode` | `Tests/ArgumentParserEndToEndTests/EnumEndToEndTests.swift:64-64` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:20-20` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:51-51` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:68-68` |
| `LongOptionWithFile` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:85-85` |
| `LongOptionWithOptionalString` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/EqualsEndToEndTests.swift:90-90` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:20-20` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:96-96` |
| `Color` | conforms | `EnumerableFlag` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:155-155` |
| `Color` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:155-155` |
| `Size` | conforms | `EnumerableFlag` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:161-161` |
| `Size` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:161-161` |
| `Shape` | conforms | `EnumerableFlag` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:193-193` |
| `Shape` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:193-193` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:199-199` |
| `Baz` | stores | `Color` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:200-201` |
| `Baz` | stores | `Size` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:203-204` |
| `Baz` | stores | `Shape` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:206-207` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:320-320` |
| `Qux` | stores | `Color` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:321-322` |
| `Qux` | stores | `Size` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:324-325` |
| `RepeatOK` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:362-362` |
| `RepeatOK` | stores | `Color` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:363-364` |
| `RepeatOK` | stores | `Shape` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:366-367` |
| `RepeatOK` | stores | `Size` | `Tests/ArgumentParserEndToEndTests/FlagsEndToEndTests.swift:369-370` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:20-20` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:100-100` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:133-133` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/JoinedEndToEndTests.swift:175-175` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:20-20` |
| `LongNameWithSingleDashEndToEndTests.Issue327` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:112-112` |
| `LongNameWithSingleDashEndToEndTests.JoinedItem` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/LongNameWithShortDashEndToEndTests.swift:127-127` |
| `Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:20-20` |
| `Foo.Build` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:27-27` |
| `Foo.Build` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:28-28` |
| `Foo.Package` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:34-34` |
| `Foo.Package.Clean` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:43-43` |
| `Foo.Package.Clean` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:44-44` |
| `Foo.Package.Clean` | stores | `Package` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:45-45` |
| `Foo.Package.Config` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:48-48` |
| `Foo.Package.Config` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:50-50` |
| `Foo.Package.Config` | stores | `Package` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:51-51` |
| `Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:281-281` |
| `UniqueOptions` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:285-285` |
| `Super` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:289-289` |
| `Super` | stores | `Options` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:294-294` |
| `Super.Sub1` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:296-296` |
| `Super.Sub1` | stores | `Options` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:297-297` |
| `Super.Sub2` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:300-300` |
| `Super.Sub2` | stores | `UniqueOptions` | `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift:301-301` |
| `Inner` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:24-24` |
| `Outer` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:37-37` |
| `Outer` | stores | `Inner` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:42-43` |
| `Command` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:52-52` |
| `Command` | stores | `Outer` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:55-56` |
| `DuplicatedFlagGroupCustom` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:129-129` |
| `DuplicatedFlagGroupCustomCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:134-134` |
| `DuplicatedFlagGroupCustomCommand` | stores | `DuplicatedFlagGroupCustom` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:136-136` |
| `DuplicatedFlagGroupLong` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:139-139` |
| `DuplicatedFlagGroupLongCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:143-143` |
| `DuplicatedFlagGroupLongCommand` | stores | `DuplicatedFlagGroupLong` | `Tests/ArgumentParserEndToEndTests/OptionGroupEndToEndTests.swift:146-146` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:20-20` |
| `Foo.Name` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:21-21` |
| `Foo.Name` | conforms | `RawRepresentable` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:21-21` |
| `Foo` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:24-24` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:57-57` |
| `Bar.Format` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:59-59` |
| `Bar.Format` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:59-59` |
| `Bar` | stores | `Format` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:65-65` |
| `OptionalEndToEndTests.Command` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:232-232` |
| `OptionalEndToEndTests.Command.MyError` | conforms | `Error` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:233-233` |
| `OptionalEndToEndTests.Command` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:238-244` |
| `OptionalEndToEndTests.Command` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/OptionalEndToEndTests.swift:246-252` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:20-20` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:56-56` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:104-104` |
| `Wobble` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:148-148` |
| `Flob` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:203-203` |
| `BadlyFormed` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:239-239` |
| `Range<Int>` | conforms (extension) | `ArgumentParser.ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:259-259` |
| `PositionalEndToEndTests.HasRange` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/PositionalEndToEndTests.swift:271-271` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:20-20` |
| `Bar.Identifier` | conforms | `Equatable` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:21-21` |
| `Bar.Identifier` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:21-21` |
| `Bar.Identifier` | conforms | `RawRepresentable` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:21-21` |
| `Bar` | stores | `Identifier` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:25-25` |
| `LogLevel` | conforms | `CustomStringConvertible` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:55-55` |
| `LogLevel` | conforms | `RawRepresentable` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:55-55` |
| `LogLevel` | conforms (extension) | `LosslessStringConvertible` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:60-60` |
| `LogLevel` | conforms (extension) | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/RawRepresentableEndToEndTests.swift:66-66` |
| `AllUnrecognizedArgs` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:19-19` |
| `AllUnrecognizedRoot` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:80-80` |
| `AllUnrecognizedRoot.Child` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:87-87` |
| `AllUnrecognizedRoot.Child` | stores | `AllUnrecognizedRoot` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:91-91` |
| `PostTerminatorArgs` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:128-128` |
| `PassthroughArgs` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests+ParsingStrategy.swift:184-184` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:21-21` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:47-47` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:69-69` |
| `Outer` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:139-139` |
| `Inner` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:143-143` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:166-166` |
| `Wobble` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:274-274` |
| `Wobble.WobbleError` | conforms | `Error` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:275-275` |
| `Wobble.Name` | conforms | `Equatable` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:276-276` |
| `Wobble.Name` | conforms | `Sendable` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:276-276` |
| `Wobble` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:284-284` |
| `Wobble` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:285-285` |
| `Wobble` | stores | `Name` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:287-287` |
| `Weazle` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:373-373` |
| `PerformanceTest` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/RepeatingEndToEndTests.swift:402-402` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:20-20` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/ShortNameEndToEndTests.swift:90-90` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:20-20` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:66-66` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SimpleEndToEndTests.swift:109-109` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:20-20` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SingleValueParsingStrategyTests.swift:61-61` |
| `AlmostAllArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:23-23` |
| `AllOptions` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:64-64` |
| `AllFlags` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:153-153` |
| `AllFlags.E` | conforms | `EnumerableFlag` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:154-154` |
| `AllFlags.E` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:154-154` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:207-207` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:208-208` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:209-209` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:210-210` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:211-211` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:212-212` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:213-213` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:214-214` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:216-216` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:217-217` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:218-218` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:219-219` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:221-221` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:222-222` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:223-223` |
| `AllFlags` | stores | `E` | `Tests/ArgumentParserEndToEndTests/SourceCompatEndToEndTests.swift:224-224` |
| `Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:20-20` |
| `CommandA` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:27-27` |
| `CommandA` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:30-30` |
| `CommandB` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:35-35` |
| `CommandB` | stores | `Foo` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:38-38` |
| `Math` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:128-128` |
| `Math.Operation` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:129-129` |
| `Math.Operation` | conforms | `String` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:129-129` |
| `Math` | stores | `Operation` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:134-135` |
| `BaseCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:167-167` |
| `BaseCommand.BaseCommandError` | conforms | `Error` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:168-168` |
| `BaseCommand.SubCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:191-191` |
| `BaseCommand.SubCommand.SubSubCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:211-211` |
| `BaseCommand.SubCommand.SubSubCommand` | conforms | `TestableSwiftTestingParsableArguments` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:211-211` |
| `BaseCommand.SubCommand.SubSubCommand.CodingKeys` | conforms | `CodingKey` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:221-221` |
| `A` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:268-268` |
| `A.HasVersionFlag` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:273-273` |
| `A.NoVersionFlag` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/SubcommandEndToEndTests.swift:277-277` |
| `FooBarError` | conforms | `Error` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:18-18` |
| `FooOption` | conforms | `Convert` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:38-38` |
| `FooOption` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:38-38` |
| `BarOption` | conforms | `Convert` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:53-53` |
| `BarOption` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:53-53` |
| `FooArgument` | conforms | `Convert` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:123-123` |
| `FooArgument` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:123-123` |
| `FooArgument.FooError` | conforms | `Error` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:131-131` |
| `BarArgument` | conforms | `Convert` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:141-141` |
| `BarArgument` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/TransformEndToEndTests.swift:141-141` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:20-20` |
| `Quizzo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:26-26` |
| `Hogeraa` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:68-68` |
| `Hogera` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:72-72` |
| `Piyo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:81-81` |
| `Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:148-148` |
| `Foo` | stores | `Config` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:150-150` |
| `Foo` | stores | `OptionalArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:151-151` |
| `Foo` | stores | `DefaultedArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:152-152` |
| `Config` | conforms | `Decodable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:155-155` |
| `OptionalArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:160-160` |
| `DefaultedArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:165-165` |
| `Barr` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:201-201` |
| `Barr` | stores | `Baz` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:202-202` |
| `Bar` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:205-205` |
| `Bar` | stores | `Baz` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:207-207` |
| `Bar` | stores | `Bazz` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:208-208` |
| `Baz` | conforms | `Decodable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:217-217` |
| `Bazz` | conforms | `Decodable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:222-222` |
| `Bamf` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:318-318` |
| `Qiqi` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:337-337` |
| `Qiqi` | stores | `Qiqii` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:339-339` |
| `Qiqii` | conforms | `Codable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:342-342` |
| `Qiqii` | conforms | `Equatable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:342-342` |
| `Fry` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:364-364` |
| `Fry` | stores | `Vig` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:366-366` |
| `Toks` | conforms | `Codable` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:369-369` |
| `Vig` | inherits | `Toks` | `Tests/ArgumentParserEndToEndTests/UnparsedValuesEndToEndTest.swift:373-373` |
| `UserValidationError` | conforms | `LocalizedError` | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:19-19` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:30-30` |
| `FooCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:161-161` |
| `ValidateCountingArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:186-186` |
| `ValidateCountingCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserEndToEndTests/ValidationEndToEndTests.swift:194-194` |
| `Simple` | conforms | `ParsableArguments` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:170-170` |
| `CustomHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:196-196` |
| `NoHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:219-219` |
| `SubCommandCustomHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:253-253` |
| `SubCommandCustomHelp.InheritHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:258-258` |
| `SubCommandCustomHelp.ModifiedHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:262-262` |
| `SubCommandCustomHelp.ModifiedHelp.InheritImmediateParentdHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/HelpTests.swift:267-267` |
| `Package.Clean` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Clean.swift:15-15` |
| `Package.Clean` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Clean.swift:16-17` |
| `Package.Config` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:16-16` |
| `Package.Config.GetMirror` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:24-24` |
| `Package.Config.GetMirror` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:25-26` |
| `Package.Config.SetMirror` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:34-34` |
| `Package.Config.SetMirror` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:35-36` |
| `Package.Config.UnsetMirror` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:47-47` |
| `Package.Config.UnsetMirror` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Config.swift:48-49` |
| `Package.Describe` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:16-16` |
| `Package.Describe` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:17-18` |
| `Package.Describe` | stores | `OutputType` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:20-21` |
| `Package.Describe.OutputType` | conforms | `Decodable` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:23-23` |
| `Package.Describe.OutputType` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:23-23` |
| `Package.Describe.OutputType` | conforms | `String` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Describe.swift:23-23` |
| `Package.GenerateXcodeProject` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:16-16` |
| `Package.GenerateXcodeProject` | stores | `Options` | `Tests/ArgumentParserPackageManagerTests/PackageManager/GenerateXcodeProject.swift:20-21` |
| `Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:14-14` |
| `Options.Configuration` | conforms | `Decodable` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:18-18` |
| `Options.Configuration` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:18-18` |
| `Options.Configuration` | conforms | `String` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:18-18` |
| `Options` | stores | `Configuration` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:23-26` |
| `Package` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:107-107` |
| `Package.Hidden` | conforms | `ParsableCommand` | `Tests/ArgumentParserPackageManagerTests/PackageManager/Options.swift:116-116` |
| `DecodingError` | conforms (extension) | `Swift.CustomStringConvertible` | `Tests/ArgumentParserToolInfoTests/ArgumentParserToolInfoTests.swift:16-16` |
| `SerializedTests.CompletionScriptTests.Path` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:40-40` |
| `SerializedTests.CompletionScriptTests.Kind` | conforms | `CustomStringConvertible` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:52-52` |
| `SerializedTests.CompletionScriptTests.Kind` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:52-52` |
| `SerializedTests.CompletionScriptTests.Kind` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:52-52` |
| `SerializedTests.CompletionScriptTests.Kind` | conforms | `String` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:52-52` |
| `SerializedTests.CompletionScriptTests.NestedArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:62-62` |
| `SerializedTests.CompletionScriptTests.Base` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:67-67` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Kind` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:73-73` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Kind` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:74-74` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Path` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:76-76` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Path` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:77-77` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Path` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:78-78` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `Kind` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:81-81` |
| `SerializedTests.CompletionScriptTests.Base` | stores | `NestedArguments` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:89-89` |
| `SerializedTests.CompletionScriptTests.Base.SubCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:91-91` |
| `SerializedTests.CompletionScriptTests.Base.HiddenChild` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:96-96` |
| `SerializedTests.CompletionScriptTests.Base.EscapedCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:100-100` |
| `SerializedTests.CompletionScriptTests.Custom` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:159-159` |
| `SerializedTests.CompletionScriptTests.Custom` | stores | `NestedArguments` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:175-175` |
| `SerializedTests.CompletionScriptTests.Custom.NestedArguments` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:177-177` |
| `SerializedTests.CompletionScriptTests.CustomAsync` | conforms | `AsyncParsableCommand` | `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift:183-183` |
| `SerializedTests.DefaultAsFlagCompletionTests.DefaultAsFlagCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DefaultAsFlagCompletionTests.swift:45-45` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:28-28` |
| `DefaultAsFlagDumpHelpTests.DefaultAsFlagWithTransformCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DefaultAsFlagDumpHelpTests.swift:46-46` |
| `DumpHelpGenerationTests.A` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:56-56` |
| `DumpHelpGenerationTests.A.TestEnum` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:57-57` |
| `DumpHelpGenerationTests.A.TestEnum` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:57-57` |
| `DumpHelpGenerationTests.A.TestEnum` | conforms | `String` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:57-57` |
| `DumpHelpGenerationTests.A` | stores | `TestEnum` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:63-64` |
| `DumpHelpGenerationTests.A` | stores | `TestEnum` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:66-67` |
| `DumpHelpGenerationTests.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:88-88` |
| `DumpHelpGenerationTests.B` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:96-96` |
| `DumpHelpGenerationTests.B` | stores | `Options` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:97-98` |
| `DumpHelpGenerationTests.C` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:101-101` |
| `DumpHelpGenerationTests.C.Color` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:104-104` |
| `DumpHelpGenerationTests.C.Color` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:104-104` |
| `DumpHelpGenerationTests.C.Color` | conforms | `String` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:104-104` |
| `DumpHelpGenerationTests.C` | stores | `Color` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:121-122` |
| `DumpHelpGenerationTests.C` | stores | `Color` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:124-125` |
| `DumpHelpGenerationTests.C` | stores | `Color` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:127-128` |
| `DumpHelpGenerationTests.C` | stores | `Color` | `Tests/ArgumentParserUnitTests/DumpHelpGenerationTests.swift:130-134` |
| `ErrorCase` | conforms | `CustomTestStringConvertible` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:17-17` |
| `ErrorCase` | conforms | `Sendable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:17-17` |
| `Bar` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:28-28` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:34-34` |
| `Format` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` |
| `Format` | conforms | `Decodable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` |
| `Format` | conforms | `Equatable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` |
| `Format` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` |
| `Format` | conforms | `String` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:83-83` |
| `Name` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` |
| `Name` | conforms | `Decodable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` |
| `Name` | conforms | `Equatable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` |
| `Name` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` |
| `Name` | conforms | `String` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:91-91` |
| `Counter` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:103-103` |
| `Counter` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:103-103` |
| `Counter` | conforms | `Int` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:103-103` |
| `Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:108-108` |
| `Foo` | stores | `Format` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:109-110` |
| `Foo` | stores | `Name` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:111-112` |
| `EnumWithFewCasesArrayArgument` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:115-115` |
| `EnumWithFewCasesArrayArgument` | stores | `Format` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:116-117` |
| `EnumWithManyCasesArrayArgument` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:120-120` |
| `EnumWithManyCasesArrayArgument` | stores | `Name` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:121-122` |
| `EnumWithIntRawValue` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:125-125` |
| `EnumWithIntRawValue` | stores | `Counter` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:126-126` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:130-130` |
| `Baz` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:208-208` |
| `Qux` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:222-222` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:231-231` |
| `Qwz` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:252-252` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:258-258` |
| `Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:291-291` |
| `Options.OutputBehaviour` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:292-292` |
| `Options.OutputBehaviour` | conforms | `String` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:292-292` |
| `Options` | stores | `OutputBehaviour` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:300-301` |
| `OptOptions` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:306-306` |
| `OptOptions.OutputBehaviour` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:307-307` |
| `OptOptions.OutputBehaviour` | conforms | `String` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:307-307` |
| `OptOptions` | stores | `OutputBehaviour` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:315-316` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:320-320` |
| `EmptyArray` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:361-361` |
| `ErrorMessageTests` | stores | `ErrorCase` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:370-370` |
| `Repeat` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ErrorMessageTests.swift:401-401` |
| `ExitCodeTests.A` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:23-23` |
| `ExitCodeTests.E` | conforms | `Error` | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:24-24` |
| `ExitCodeTests.C` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ExitCodeTests.swift:25-25` |
| `HelpGenerationTests.AtArgumentTransform.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:26-26` |
| `HelpGenerationTests.AtArgumentTransform.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:27-28` |
| `HelpGenerationTests.AtArgumentTransform.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:31-31` |
| `HelpGenerationTests.AtArgumentTransform.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:32-33` |
| `HelpGenerationTests.AtArgumentTransform.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:36-36` |
| `HelpGenerationTests.AtArgumentTransform.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:37-38` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:41-41` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:42-43` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:46-46` |
| `HelpGenerationTests.AtArgumentTransform.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:47-48` |
| `HelpGenerationTests.AtArgumentTransform.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:51-51` |
| `HelpGenerationTests.AtArgumentTransform.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:52-53` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:56-56` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:57-58` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:61-61` |
| `HelpGenerationTests.AtArgumentTransform.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:62-63` |
| `HelpGenerationTests.AtArgumentEBA.A` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:200-200` |
| `HelpGenerationTests.AtArgumentEBA.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:207-207` |
| `HelpGenerationTests.AtArgumentEBA.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:208-209` |
| `HelpGenerationTests.AtArgumentEBA.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:212-212` |
| `HelpGenerationTests.AtArgumentEBA.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:213-214` |
| `HelpGenerationTests.AtArgumentEBA.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:217-217` |
| `HelpGenerationTests.AtArgumentEBA.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:218-219` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:222-222` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:223-224` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:227-228` |
| `HelpGenerationTests.AtArgumentEBA.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:229-230` |
| `HelpGenerationTests.AtArgumentEBA.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:233-233` |
| `HelpGenerationTests.AtArgumentEBA.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:234-235` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:238-238` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:239-240` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:243-243` |
| `HelpGenerationTests.AtArgumentEBA.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:244-245` |
| `HelpGenerationTests.AtArgumentEBATransform.A` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:366-366` |
| `HelpGenerationTests.AtArgumentEBATransform.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:373-373` |
| `HelpGenerationTests.AtArgumentEBATransform.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:374-375` |
| `HelpGenerationTests.AtArgumentEBATransform.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:378-378` |
| `HelpGenerationTests.AtArgumentEBATransform.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:379-380` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:383-383` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:384-385` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:388-388` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:389-390` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:393-393` |
| `HelpGenerationTests.AtArgumentEBATransform.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:394-395` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:398-398` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:399-400` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:403-403` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:404-405` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:408-408` |
| `HelpGenerationTests.AtArgumentEBATransform.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtArgument.swift:409-410` |
| `HelpGenerationTests.AtOptionTransform.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:26-26` |
| `HelpGenerationTests.AtOptionTransform.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:27-28` |
| `HelpGenerationTests.AtOptionTransform.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:31-31` |
| `HelpGenerationTests.AtOptionTransform.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:32-33` |
| `HelpGenerationTests.AtOptionTransform.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:36-36` |
| `HelpGenerationTests.AtOptionTransform.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:37-38` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:41-41` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:42-43` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:46-46` |
| `HelpGenerationTests.AtOptionTransform.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:47-48` |
| `HelpGenerationTests.AtOptionTransform.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:51-51` |
| `HelpGenerationTests.AtOptionTransform.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:52-53` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:56-56` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:57-58` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:61-61` |
| `HelpGenerationTests.AtOptionTransform.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:62-63` |
| `HelpGenerationTests.AtOptionEBA.A` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:176-176` |
| `HelpGenerationTests.AtOptionEBA.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:183-183` |
| `HelpGenerationTests.AtOptionEBA.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:184-185` |
| `HelpGenerationTests.AtOptionEBA.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:188-188` |
| `HelpGenerationTests.AtOptionEBA.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:189-190` |
| `HelpGenerationTests.AtOptionEBA.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:193-193` |
| `HelpGenerationTests.AtOptionEBA.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:194-195` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:198-198` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:199-200` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:203-204` |
| `HelpGenerationTests.AtOptionEBA.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:205-206` |
| `HelpGenerationTests.AtOptionEBA.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:209-209` |
| `HelpGenerationTests.AtOptionEBA.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:210-211` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:214-214` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:215-216` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:219-219` |
| `HelpGenerationTests.AtOptionEBA.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:220-221` |
| `HelpGenerationTests.AtOptionEBATransform.A` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:321-321` |
| `HelpGenerationTests.AtOptionEBATransform.BareNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:328-328` |
| `HelpGenerationTests.AtOptionEBATransform.BareNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:329-330` |
| `HelpGenerationTests.AtOptionEBATransform.BareDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:333-333` |
| `HelpGenerationTests.AtOptionEBATransform.BareDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:334-335` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:338-338` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:339-340` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefaultNil` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:343-343` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefaultNil` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:344-345` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:348-348` |
| `HelpGenerationTests.AtOptionEBATransform.OptionalDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:349-350` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayNoDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:353-353` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayNoDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:354-355` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefaultEmpty` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:358-358` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefaultEmpty` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:359-360` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:363-363` |
| `HelpGenerationTests.AtOptionEBATransform.ArrayDefault` | stores | `A` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOption.swift:364-365` |
| `HelpGenerationTests.BasicDefaultAsFlag` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:19-19` |
| `HelpGenerationTests.DefaultAsFlagWithShortNames` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:64-64` |
| `HelpGenerationTests.MixedOptionTypes` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+AtOptionDefaultAsFlag.swift:91-91` |
| `HelpGenerationTests.Flags` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:21-21` |
| `HelpGenerationTests.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:29-29` |
| `HelpGenerationTests.FlagsAndOptions` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:37-37` |
| `HelpGenerationTests.ArgsAndFlags` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:45-45` |
| `HelpGenerationTests.AllVisible` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:56-56` |
| `HelpGenerationTests.AllVisible` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:57-58` |
| `HelpGenerationTests.AllVisible` | stores | `Options` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:60-61` |
| `HelpGenerationTests.AllVisible` | stores | `FlagsAndOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:63-64` |
| `HelpGenerationTests.AllVisible` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:66-67` |
| `HelpGenerationTests.ContainsOptionGroup` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:70-70` |
| `HelpGenerationTests.ContainsOptionGroup` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:71-72` |
| `HelpGenerationTests.ContainsOptionGroup` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:74-75` |
| `HelpGenerationTests.Combined` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:129-129` |
| `HelpGenerationTests.Combined` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:130-131` |
| `HelpGenerationTests.Combined` | stores | `Options` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:133-134` |
| `HelpGenerationTests.Combined` | stores | `FlagsAndOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:136-137` |
| `HelpGenerationTests.Combined` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:139-140` |
| `HelpGenerationTests.HiddenGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:190-190` |
| `HelpGenerationTests.HiddenGroups` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:191-192` |
| `HelpGenerationTests.HiddenGroups` | stores | `Options` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:194-195` |
| `HelpGenerationTests.HiddenGroups` | stores | `FlagsAndOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:197-198` |
| `HelpGenerationTests.HiddenGroups` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:200-201` |
| `HelpGenerationTests.NestedGroups` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:236-236` |
| `HelpGenerationTests.NestedGroups` | stores | `FlagsAndOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:237-238` |
| `HelpGenerationTests.NestedGroups` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:240-241` |
| `HelpGenerationTests.NestedHiddenGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:244-244` |
| `HelpGenerationTests.NestedHiddenGroups` | stores | `NestedGroups` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:245-246` |
| `HelpGenerationTests.ParentWithGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:273-273` |
| `HelpGenerationTests.ParentWithGroups` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:278-279` |
| `HelpGenerationTests.ParentWithGroups` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:281-282` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:284-284` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | stores | `Flags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:285-286` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | stores | `Options` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:288-289` |
| `HelpGenerationTests.ParentWithGroups.ChildWithGroups` | stores | `ArgsAndFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:291-292` |
| `HelpGenerationTests.GroupsWithUnnamedGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:390-390` |
| `HelpGenerationTests.GroupsWithUnnamedGroups` | stores | `ContainsOptionGroup` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:391-392` |
| `HelpGenerationTests.GroupsWithNamedGroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:415-415` |
| `HelpGenerationTests.GroupsWithNamedGroups` | stores | `ContainsOptionGroup` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+GroupName.swift:416-417` |
| `HelpGenerationTests.Root` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:21-21` |
| `HelpGenerationTests.Root.Inherits` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:28-28` |
| `HelpGenerationTests.Root.Inherits.Nested` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:33-33` |
| `HelpGenerationTests.Root.Overrides` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:39-39` |
| `HelpGenerationTests.Root.Overrides.Nested` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:45-45` |
| `HelpGenerationTests.Root.Suppresses` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:51-51` |
| `HelpGenerationTests.NoBanner` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:147-147` |
| `HelpGenerationTests.VerbatimBanner` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:167-167` |
| `HelpGenerationTests.BannerNoAbstract` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests+HelpBanner.swift:198-198` |
| `Foundation.URL` | conforms (extension) | `ArgumentParser.ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:23-23` |
| `HelpGenerationTests.A` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:39-39` |
| `HelpGenerationTests.B` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:58-58` |
| `HelpGenerationTests.C` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:102-102` |
| `HelpGenerationTests.Issue27` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:124-124` |
| `HelpGenerationTests.OptionFlags` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:151-151` |
| `HelpGenerationTests.OptionFlags` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:151-151` |
| `HelpGenerationTests.D` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:170-170` |
| `HelpGenerationTests.D` | stores | `OptionFlags` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:188-189` |
| `HelpGenerationTests.D` | stores | `Degree` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:191-192` |
| `HelpGenerationTests.D.Manual` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:197-197` |
| `HelpGenerationTests.D.Manual` | conforms | `Int` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:197-197` |
| `HelpGenerationTests.D` | stores | `Manual` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:201-202` |
| `HelpGenerationTests.D.UnspecializedSynthesized` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:204-204` |
| `HelpGenerationTests.D.UnspecializedSynthesized` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:204-204` |
| `HelpGenerationTests.D.UnspecializedSynthesized` | conforms | `Int` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:204-204` |
| `HelpGenerationTests.D` | stores | `UnspecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:207-208` |
| `HelpGenerationTests.D.SpecializedSynthesized` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:210-210` |
| `HelpGenerationTests.D.SpecializedSynthesized` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:210-210` |
| `HelpGenerationTests.D.SpecializedSynthesized` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:210-210` |
| `HelpGenerationTests.D` | stores | `SpecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:214-215` |
| `HelpGenerationTests.E` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:244-244` |
| `HelpGenerationTests.E.OutputBehaviour` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:245-245` |
| `HelpGenerationTests.E.OutputBehaviour` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:245-245` |
| `HelpGenerationTests.E` | stores | `OutputBehaviour` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:253-254` |
| `HelpGenerationTests.F` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:257-257` |
| `HelpGenerationTests.F.OutputBehaviour` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:258-258` |
| `HelpGenerationTests.F.OutputBehaviour` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:258-258` |
| `HelpGenerationTests.F` | stores | `OutputBehaviour` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:266-267` |
| `HelpGenerationTests.G` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:270-270` |
| `HelpGenerationTests.H` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:311-311` |
| `HelpGenerationTests.H.CommandWithVeryLongName` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:312-312` |
| `HelpGenerationTests.H.ShortCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:313-313` |
| `HelpGenerationTests.H.ShortCommand` | stores | `CommandConfiguration` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:314-314` |
| `HelpGenerationTests.H.AnotherCommandWithVeryLongName` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:317-317` |
| `HelpGenerationTests.H.AnotherCommandWithVeryLongName` | stores | `CommandConfiguration` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:318-318` |
| `HelpGenerationTests.H.AnotherCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:321-321` |
| `HelpGenerationTests.I` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:381-381` |
| `HelpGenerationTests.J` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:399-399` |
| `HelpGenerationTests.K` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:420-420` |
| `HelpGenerationTests.L` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:446-446` |
| `HelpGenerationTests.M` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:471-471` |
| `HelpGenerationTests.N` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:473-473` |
| `HelpGenerationTests.O` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:494-494` |
| `HelpGenerationTests.O` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:494-494` |
| `HelpGenerationTests.P` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:506-506` |
| `HelpGenerationTests.P` | stores | `O` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:507-508` |
| `HelpGenerationTests.P` | stores | `O` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:510-511` |
| `HelpGenerationTests.Foo` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:530-530` |
| `HelpGenerationTests.Bar` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:545-545` |
| `HelpGenerationTests.WithSubgroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:574-574` |
| `HelpGenerationTests.OnlySubgroups` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:611-611` |
| `HelpGenerationTests.OptionsToHide` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:650-650` |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:664-665` |
| `HelpGenerationTests.HideOptionGroupLegacyDriver` | stores | `OptionsToHide` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:669-670` |
| `HelpGenerationTests.HideOptionGroupDriver` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:676-676` |
| `HelpGenerationTests.HideOptionGroupDriver` | stores | `OptionsToHide` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:680-681` |
| `HelpGenerationTests.PrivateOptionGroupDriver` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:687-687` |
| `HelpGenerationTests.PrivateOptionGroupDriver` | stores | `OptionsToHide` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:691-692` |
| `HelpGenerationTests.AllValues` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:752-752` |
| `HelpGenerationTests.AllValues.Manual` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:753-753` |
| `HelpGenerationTests.AllValues.Manual` | conforms | `Int` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:753-753` |
| `HelpGenerationTests.AllValues.UnspecializedSynthesized` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:758-758` |
| `HelpGenerationTests.AllValues.UnspecializedSynthesized` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:758-758` |
| `HelpGenerationTests.AllValues.UnspecializedSynthesized` | conforms | `Int` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:758-758` |
| `HelpGenerationTests.AllValues.SpecializedSynthesized` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:762-762` |
| `HelpGenerationTests.AllValues.SpecializedSynthesized` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:762-762` |
| `HelpGenerationTests.AllValues.SpecializedSynthesized` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:762-762` |
| `HelpGenerationTests.AllValues` | stores | `Manual` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:767-767` |
| `HelpGenerationTests.AllValues` | stores | `Manual` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:768-768` |
| `HelpGenerationTests.AllValues` | stores | `UnspecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:770-770` |
| `HelpGenerationTests.AllValues` | stores | `UnspecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:771-771` |
| `HelpGenerationTests.AllValues` | stores | `SpecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:773-773` |
| `HelpGenerationTests.AllValues` | stores | `SpecializedSynthesized` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:774-774` |
| `HelpGenerationTests.Q` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:807-807` |
| `HelpGenerationTests.ParserBug` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:836-836` |
| `HelpGenerationTests.ParserBug.CommonOptions` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:841-841` |
| `HelpGenerationTests.ParserBug.Sub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:846-846` |
| `HelpGenerationTests.ParserBug.Sub` | stores | `CommonOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:847-848` |
| `HelpGenerationTests.NonCustomUsage` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:873-873` |
| `HelpGenerationTests.NonCustomUsage.ExampleSubcommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:874-874` |
| `HelpGenerationTests.CustomUsageShort` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:886-886` |
| `HelpGenerationTests.CustomUsageLong` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:896-896` |
| `HelpGenerationTests.CustomUsageHidden` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:908-908` |
| `HelpGenerationTests.OptionValues` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1065-1065` |
| `HelpGenerationTests.OptionValues` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1065-1065` |
| `HelpGenerationTests.OptionValues` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1065-1065` |
| `HelpGenerationTests.CustomOption` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1082-1082` |
| `HelpGenerationTests.CustomOption` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1083-1083` |
| `HelpGenerationTests.CustomOptionAsListWithSingleDefaultValue` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1102-1102` |
| `HelpGenerationTests.CustomOptionAsListWithSingleDefaultValue` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1103-1105` |
| `HelpGenerationTests.CustomOptionAsListWithMultipleDefaultValue` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1126-1126` |
| `HelpGenerationTests.CustomOptionAsListWithMultipleDefaultValue` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1127-1129` |
| `HelpGenerationTests.CustomOptionAsListWithEmptyArrayAsDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1151-1151` |
| `HelpGenerationTests.CustomOptionAsListWithEmptyArrayAsDefault` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1152-1154` |
| `HelpGenerationTests.CustomOptionWithDefault` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1176-1176` |
| `HelpGenerationTests.CustomOptionWithDefault` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1177-1178` |
| `HelpGenerationTests.Optional` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1198-1198` |
| `HelpGenerationTests.Optional` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1199-1199` |
| `HelpGenerationTests.NoAbstract` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1218-1218` |
| `HelpGenerationTests.NoAbstract` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1219-1219` |
| `HelpGenerationTests.NoAbstract` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1220-1220` |
| `HelpGenerationTests.Preamble` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1244-1244` |
| `HelpGenerationTests.Preamble` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1245-1255` |
| `HelpGenerationTests.Preamble` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1257-1264` |
| `HelpGenerationTests.OptionWithoutEnumerationHelpText` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1290-1290` |
| `HelpGenerationTests.OptionWithoutEnumerationHelpText` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1290-1290` |
| `HelpGenerationTests.OptionWithoutEnumerationHelpText` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1290-1290` |
| `HelpGenerationTests.HelpTextComparison` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1298-1298` |
| `HelpGenerationTests.HelpTextComparison` | stores | `OptionValues` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1299-1300` |
| `HelpGenerationTests.HelpTextComparison` | stores | `OptionWithoutEnumerationHelpText` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1302-1304` |
| `HelpGenerationTests.Empty` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1329-1329` |
| `HelpGenerationTests.Empty` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1329-1329` |
| `HelpGenerationTests.EmptyCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1339-1339` |
| `HelpGenerationTests.EmptyCommand` | stores | `Empty` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1340-1340` |
| `HelpGenerationTests.Cases` | conforms | `CaseIterable` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1358-1358` |
| `HelpGenerationTests.Cases` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1358-1358` |
| `HelpGenerationTests.Cases` | conforms | `String` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1358-1358` |
| `HelpGenerationTests.LongLabelHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1380-1380` |
| `HelpGenerationTests.LongLabelHelp` | stores | `Cases` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1381-1384` |
| `HelpGenerationTests.LongLabelHelpWithOptionDescription` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1410-1410` |
| `HelpGenerationTests.LongLabelHelpWithOptionDescription` | stores | `Cases` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1411-1418` |
| `HelpGenerationTests.WideHelp` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1449-1449` |
| `HelpGenerationTests.OptionGroupOptions` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1505-1505` |
| `HelpGenerationTests.OptionGroupCommand` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1510-1510` |
| `HelpGenerationTests.OptionGroupCommand` | stores | `OptionGroupOptions` | `Tests/ArgumentParserUnitTests/HelpGenerationTests.swift:1513-1514` |
| `InputOriginTests.IsDefaultTestData` | conforms | `CustomTestStringConvertible` | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:20-20` |
| `InputOriginTests.IsDefaultTestData` | stores | `Element` | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:22-22` |
| `InputOriginTests.IsDefaultTestData` | stores | `InputOrigin` | `Tests/ArgumentParserUnitTests/InputOriginTests.swift:22-22` |
| `ParsableArgumentsValidationTests.A` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:18-18` |
| `ParsableArgumentsValidationTests.A.CodingKeys` | conforms | `CodingKey` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:25-25` |
| `ParsableArgumentsValidationTests.A.CodingKeys` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:25-25` |
| `ParsableArgumentsValidationTests.B` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:33-33` |
| `ParsableArgumentsValidationTests.C` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:43-43` |
| `ParsableArgumentsValidationTests.C.CodingKeys` | conforms | `CodingKey` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:50-50` |
| `ParsableArgumentsValidationTests.C.CodingKeys` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:50-50` |
| `ParsableArgumentsValidationTests.D` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:57-57` |
| `ParsableArgumentsValidationTests.D.CodingKeys` | conforms | `CodingKey` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:64-64` |
| `ParsableArgumentsValidationTests.D.CodingKeys` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:64-64` |
| `ParsableArgumentsValidationTests.E` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:69-69` |
| `ParsableArgumentsValidationTests.E.CodingKeys` | conforms | `CodingKey` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:79-79` |
| `ParsableArgumentsValidationTests.E.CodingKeys` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:79-79` |
| `ParsableArgumentsValidationTests.TypeWithInvalidDecoder` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:120-120` |
| `ParsableArgumentsValidationTests.AsyncCompletionOptionGroup` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:149-150` |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:173-174` |
| `ParsableArgumentsValidationTests.TypeWithInvalidAsyncCompletions` | stores | `AsyncCompletionOptionGroup` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:186-187` |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | conforms | `AsyncParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:210-211` |
| `ParsableArgumentsValidationTests.TypeWithValidAsyncCompletions` | stores | `AsyncCompletionOptionGroup` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:223-224` |
| `ParsableArgumentsValidationTests.TypeWithValidSyncCompletions` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:237-238` |
| `ParsableArgumentsValidationTests.F` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:262-262` |
| `ParsableArgumentsValidationTests.G` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:270-270` |
| `ParsableArgumentsValidationTests.H` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:278-278` |
| `ParsableArgumentsValidationTests.I` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:286-286` |
| `ParsableArgumentsValidationTests.I` | stores | `F` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:290-291` |
| `ParsableArgumentsValidationTests.J` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:294-294` |
| `ParsableArgumentsValidationTests.J.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:295-295` |
| `ParsableArgumentsValidationTests.J` | stores | `Options` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:300-301` |
| `ParsableArgumentsValidationTests.K` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:307-307` |
| `ParsableArgumentsValidationTests.K.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:308-308` |
| `ParsableArgumentsValidationTests.K` | stores | `Options` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:316-317` |
| `ParsableArgumentsValidationTests.L` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:321-321` |
| `ParsableArgumentsValidationTests.L.Options` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:322-322` |
| `ParsableArgumentsValidationTests.L` | stores | `Options` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:328-328` |
| `ParsableArgumentsValidationTests.DifferentNames` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:369-369` |
| `ParsableArgumentsValidationTests.TwoOfTheSameName` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:385-385` |
| `ParsableArgumentsValidationTests.MultipleUniquenessViolations` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:407-407` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:447-447` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument.Versimilitude` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:451-451` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument.Versimilitude` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:451-451` |
| `ParsableArgumentsValidationTests.MultipleNamesPerArgument` | stores | `Versimilitude` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:457-458` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:475-475` |
| `ParsableArgumentsValidationTests.FourDuplicateNames.Numbers` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:485-485` |
| `ParsableArgumentsValidationTests.FourDuplicateNames.Numbers` | conforms | `Int` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:485-485` |
| `ParsableArgumentsValidationTests.FourDuplicateNames` | stores | `Numbers` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:491-492` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:510-510` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames.ExampleEnum` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:511-511` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames.ExampleEnum` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:511-511` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersShortNames` | stores | `ExampleEnum` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:523-524` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:527-527` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames.ExampleEnum` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:528-528` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames.ExampleEnum` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:528-528` |
| `ParsableArgumentsValidationTests.DuplicatedFirstLettersLongNames` | stores | `ExampleEnum` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:536-537` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:562-562` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag.ExampleEnum` | conforms | `EnumerableFlag` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:563-563` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag.ExampleEnum` | conforms | `String` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:563-563` |
| `ParsableArgumentsValidationTests.HasOneNonsenseFlag` | stores | `ExampleEnum` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:571-572` |
| `ParsableArgumentsValidationTests.MultipleNonsenseFlags` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/ParsableArgumentsValidationTests.swift:610-610` |
| `SendableTests.MyExpressibleType` | conforms | `ExpressibleByArgument` | `Tests/ArgumentParserUnitTests/SendableTests.swift:18-18` |
| `SendableTests.SendableClassType` | conforms | `Sendable` | `Tests/ArgumentParserUnitTests/SendableTests.swift:22-22` |
| `SendableTests.Foo` | conforms | `ParsableArguments` | `Tests/ArgumentParserUnitTests/SendableTests.swift:36-36` |
| `SendableTests.Foo` | conforms | `Sendable` | `Tests/ArgumentParserUnitTests/SendableTests.swift:36-36` |
| `SendableTests.Foo` | stores | `MyExpressibleType` | `Tests/ArgumentParserUnitTests/SendableTests.swift:40-41` |
| `SendableTests.Foo` | stores | `SendableClassType` | `Tests/ArgumentParserUnitTests/SendableTests.swift:43-44` |
| `SendableTests.Foo` | stores | `SendableClassType` | `Tests/ArgumentParserUnitTests/SendableTests.swift:46-47` |
| `SendableTests.Foo` | stores | `MyExpressibleType` | `Tests/ArgumentParserUnitTests/SendableTests.swift:49-50` |
| `SendableTests.Bar` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/SendableTests.swift:53-53` |
| `SendableTests.Bar` | conforms | `Sendable` | `Tests/ArgumentParserUnitTests/SendableTests.swift:53-53` |
| `SendableTests.Bar` | stores | `Foo` | `Tests/ArgumentParserUnitTests/SendableTests.swift:54-55` |
| `SendableTests.Baz` | conforms | `AsyncParsableCommand` | `Tests/ArgumentParserUnitTests/SendableTests.swift:58-58` |
| `SendableTests.Baz` | conforms | `Sendable` | `Tests/ArgumentParserUnitTests/SendableTests.swift:58-58` |
| `SendableTests.Baz` | stores | `Foo` | `Tests/ArgumentParserUnitTests/SendableTests.swift:59-60` |
| `ArgumentParser.SplitArguments.InputIndex` | conforms (extension) | `Swift .ExpressibleByIntegerLiteral` | `Tests/ArgumentParserUnitTests/SplitArgumentTests.swift:17-17` |
| `TreeTests.A` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:58-58` |
| `TreeTests.Root` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:61-61` |
| `TreeTests.Sub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:64-64` |
| `TreeTests.RootWithNamedNestedSub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:68-68` |
| `TreeTests.RootWithNamedNestedSub.NestedSub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:73-73` |
| `TreeTests.RootWithNestedSub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:79-79` |
| `TreeTests.RootWithNestedSub.NestedSub` | conforms | `ParsableCommand` | `Tests/ArgumentParserUnitTests/TreeTests.swift:84-84` |
| `ChangelogAuthors` | conforms | `AsyncParsableCommand` | `Tools/changelog-authors/ChangelogAuthors.swift:19-21` |
| `Comparison` | conforms | `Codable` | `Tools/changelog-authors/Models.swift:14-14` |
| `Comparison` | stores | `Commit` | `Tools/changelog-authors/Models.swift:15-15` |
| `Commit` | conforms | `Codable` | `Tools/changelog-authors/Models.swift:18-18` |
| `Commit` | stores | `Author` | `Tools/changelog-authors/Models.swift:20-20` |
| `Author` | conforms | `Codable` | `Tools/changelog-authors/Models.swift:23-23` |
| `Author.CodingKeys` | conforms | `CodingKey` | `Tools/changelog-authors/Models.swift:27-27` |
| `Author.CodingKeys` | conforms | `String` | `Tools/changelog-authors/Models.swift:27-27` |
| `SubprocessError` | conforms | `CustomStringConvertible` | `Tools/generate-docc-reference/Extensions/Process+SimpleAPI.swift:14-14` |
| `SubprocessError` | conforms | `LocalizedError` | `Tools/generate-docc-reference/Extensions/Process+SimpleAPI.swift:14-14` |
| `SubprocessError` | conforms | `Swift.Error` | `Tools/generate-docc-reference/Extensions/Process+SimpleAPI.swift:14-14` |
| `GenerateDoccReferenceError` | conforms | `Error` | `Tools/generate-docc-reference/GenerateDoccReference.swift:16-16` |
| `GenerateDoccReferenceError` | conforms (extension) | `CustomStringConvertible` | `Tools/generate-docc-reference/GenerateDoccReference.swift:23-23` |
| `OutputStyle` | conforms | `EnumerableFlag` | `Tools/generate-docc-reference/GenerateDoccReference.swift:40-40` |
| `OutputStyle` | conforms | `ExpressibleByArgument` | `Tools/generate-docc-reference/GenerateDoccReference.swift:40-40` |
| `OutputStyle` | conforms | `String` | `Tools/generate-docc-reference/GenerateDoccReference.swift:40-40` |
| `GenerateDoccReference` | conforms | `ParsableCommand` | `Tools/generate-docc-reference/GenerateDoccReference.swift:47-48` |
| `GenerateDoccReference` | stores | `OutputStyle` | `Tools/generate-docc-reference/GenerateDoccReference.swift:61-64` |
| `AuthorArgument` | conforms (extension) | `ExpressibleByArgument` | `Tools/generate-manual/AuthorArgument.swift:41-41` |
| `ArgumentSynopsis` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/ArgumentSynopsis.swift:15-15` |
| `ArgumentSynopsis` | stores | `ArgumentInfoV0` | `Tools/generate-manual/DSL/ArgumentSynopsis.swift:16-16` |
| `Author` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Author.swift:15-15` |
| `Author` | stores | `AuthorArgument` | `Tools/generate-manual/DSL/Author.swift:16-16` |
| `Authors` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Authors.swift:15-15` |
| `Authors` | stores | `AuthorArgument` | `Tools/generate-manual/DSL/Authors.swift:16-16` |
| `Container` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Core/Container.swift:15-15` |
| `Empty` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Core/Empty.swift:12-12` |
| `ForEach` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Core/ForEach.swift:12-12` |
| `ForEach` | stores | `C` | `Tools/generate-manual/DSL/Core/ForEach.swift:13-13` |
| `ForEach` | stores | `C` | `Tools/generate-manual/DSL/Core/ForEach.swift:14-14` |
| `ForEach` | stores | `Element` | `Tools/generate-manual/DSL/Core/ForEach.swift:14-14` |
| `ForEach` | stores | `Index` | `Tools/generate-manual/DSL/Core/ForEach.swift:14-14` |
| `MDocASTNodeWrapper` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Core/MDocASTNodeWrapper.swift:12-12` |
| `DiscussionText` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Discussion.swift:14-14` |
| `Document` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Document.swift:16-16` |
| `Document` | stores | `AuthorArgument` | `Tools/generate-manual/DSL/Document.swift:20-20` |
| `Document` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/Document.swift:21-21` |
| `DocumentDate` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/DocumentDate.swift:16-16` |
| `Exit` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Exit.swift:15-15` |
| `List` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/List.swift:12-12` |
| `MultiPageDescription` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/MultiPageDescription.swift:15-15` |
| `MultiPageDescription` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/MultiPageDescription.swift:16-16` |
| `Name` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Name.swift:15-15` |
| `Name` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/Name.swift:16-16` |
| `Preamble` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Preamble.swift:16-16` |
| `Preamble` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/Preamble.swift:19-19` |
| `Section` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Section.swift:12-12` |
| `SeeAlso` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/SeeAlso.swift:15-15` |
| `SeeAlso` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/SeeAlso.swift:17-17` |
| `SinglePageDescription` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/SinglePageDescription.swift:15-15` |
| `SinglePageDescription` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/SinglePageDescription.swift:16-16` |
| `SinglePageDescription` | stores | `ArgumentInfoV0` | `Tools/generate-manual/DSL/SinglePageDescription.swift:26-26` |
| `Synopsis` | conforms | `MDocComponent` | `Tools/generate-manual/DSL/Synopsis.swift:15-15` |
| `Synopsis` | stores | `CommandInfoV0` | `Tools/generate-manual/DSL/Synopsis.swift:16-16` |
| `Foundation.Date` | conforms (extension) | `ArgumentParser.ExpressibleByArgument` | `Tools/generate-manual/Extensions/Date+ExpressibleByArgument.swift:15-15` |
| `SubprocessError` | conforms | `CustomStringConvertible` | `Tools/generate-manual/Extensions/Process+SimpleAPI.swift:14-14` |
| `SubprocessError` | conforms | `LocalizedError` | `Tools/generate-manual/Extensions/Process+SimpleAPI.swift:14-14` |
| `SubprocessError` | conforms | `Swift.Error` | `Tools/generate-manual/Extensions/Process+SimpleAPI.swift:14-14` |
| `GenerateManualError` | conforms | `Error` | `Tools/generate-manual/GenerateManual.swift:16-16` |
| `GenerateManualError` | conforms (extension) | `CustomStringConvertible` | `Tools/generate-manual/GenerateManual.swift:23-23` |
| `GenerateManual` | conforms | `ParsableCommand` | `Tools/generate-manual/GenerateManual.swift:39-40` |
| `GenerateManual` | stores | `AuthorArgument` | `Tools/generate-manual/GenerateManual.swift:59-62` |
| `Int` | conforms (extension) | `MDocASTNode` | `Tools/generate-manual/MDoc/MDocASTNode.swift:32-32` |
| `String` | conforms (extension) | `MDocASTNode` | `Tools/generate-manual/MDoc/MDocASTNode.swift:38-38` |
| `MDocMacro.Comment` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:139-139` |
| `MDocMacro.DocumentDate` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:160-160` |
| `MDocMacro.DocumentTitle` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:183-183` |
| `MDocMacro.OperatingSystem` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:221-221` |
| `MDocMacro.DocumentName` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:262-262` |
| `MDocMacro.DocumentDescription` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:283-283` |
| `MDocMacro.SectionHeader` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:309-309` |
| `MDocMacro.SubsectionHeader` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:331-331` |
| `MDocMacro.SectionReference` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:351-351` |
| `MDocMacro.CrossManualReference` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:368-368` |
| `MDocMacro.ParagraphBreak` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:386-386` |
| `MDocMacro.BeginList` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:428-428` |
| `MDocMacro.BeginList.ListStyle` | conforms | `String` | `Tools/generate-manual/MDoc/MDocMacro.swift:430-430` |
| `MDocMacro.ListItem` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:536-536` |
| `MDocMacro.EndList` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:553-553` |
| `MDocMacro.WithoutTrailingSpace` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:573-573` |
| `MDocMacro.WithoutLeadingSpace` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:590-590` |
| `MDocMacro.Apostrophe` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:607-607` |
| `MDocMacro.CommandOption` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:642-642` |
| `MDocMacro.CommandModifier` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:665-665` |
| `MDocMacro.CommandArgument` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:690-690` |
| `MDocMacro.OptionalCommandLineComponent` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:713-713` |
| `MDocMacro.BeginOptionalCommandLineComponent` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:738-738` |
| `MDocMacro.EndOptionalCommandLineComponent` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:748-748` |
| `MDocMacro.InteractiveCommand` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:770-770` |
| `MDocMacro.EnvironmentVariable` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:788-788` |
| `MDocMacro.FilePath` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:807-807` |
| `MDocMacro.Author` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:879-879` |
| `MDocMacro.Hyperlink` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:904-904` |
| `MDocMacro.MailTo` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:924-924` |
| `MDocMacro.Emphasis` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:982-982` |
| `MDocMacro.Boldface` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1005-1005` |
| `MDocMacro.NormalText` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1023-1023` |
| `MDocMacro.BeginFont` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1042-1042` |
| `MDocMacro.EndFont` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1074-1074` |
| `MDocMacro.BeginTypographicDoubleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1095-1095` |
| `MDocMacro.EndTypographicDoubleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1105-1105` |
| `MDocMacro.BeginTypewriterDoubleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1126-1126` |
| `MDocMacro.EndTypewriterDoubleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1136-1136` |
| `MDocMacro.BeginSingleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1155-1155` |
| `MDocMacro.EndSingleQuotes` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1165-1165` |
| `MDocMacro.BeginParentheses` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1184-1184` |
| `MDocMacro.EndParentheses` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1194-1194` |
| `MDocMacro.BeginSquareBrackets` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1213-1213` |
| `MDocMacro.EndSquareBrackets` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1223-1223` |
| `MDocMacro.BeginCurlyBraces` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1242-1242` |
| `MDocMacro.EndCurlyBraces` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1252-1252` |
| `MDocMacro.BeginAngleBrackets` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1271-1271` |
| `MDocMacro.EndAngleBrackets` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1281-1281` |
| `MDocMacro.ExitStandard` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1303-1303` |
| `MDocMacro.AttUnix` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1345-1345` |
| `MDocMacro.BSD` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1370-1370` |
| `MDocMacro.BSDOS` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1397-1397` |
| `MDocMacro.NetBSD` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1417-1417` |
| `MDocMacro.FreeBSD` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1437-1437` |
| `MDocMacro.OpenBSD` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1457-1457` |
| `MDocMacro.DragonFly` | conforms | `MDocMacroProtocol` | `Tools/generate-manual/MDoc/MDocMacro.swift:1477-1477` |

## Residuals

- `parse-error` `Examples/count-lines/CountLines.swift` lines 59-66 — location body; effect enclosing func run
- `parse-error` `Sources/ArgumentParser/Usage/UsageGenerator.swift` lines 317-317 — location body; effect enclosing var suggestion
- `parse-error` `Sources/ArgumentParser/Usage/UsageGenerator.swift` lines 322-322 — location body; effect enclosing var suggestion
- `parse-error` `Sources/ArgumentParser/Utilities/Mutex.swift` lines 30-30 — location member; effect enclosing struct _Lock
- `parse-error` `Sources/ArgumentParserTestHelpers/TestHelpers+SwiftTesting.swift` lines 1-604 — location top level; effect no enclosing declaration
- `parse-error` `Tests/ArgumentParserEndToEndTests/DefaultAsFlagEndToEndTests.swift` lines 182-197 — location declaration header; effect enclosing func implTestDefaultAsFlagWithTerminatorValueBeforeTerminator
- `parse-error` `Tests/ArgumentParserEndToEndTests/NestedCommandEndToEndTests.swift` lines 58-58 — location declaration header; effect enclosing func expectParseFooCommand
- `parse-error` `Tests/ArgumentParserGenerateDoccReferenceTests/GenerateDoccReferenceTests.swift` lines 16-16 — location member; effect enclosing struct GenerateDoccReferenceTests
- `parse-error` `Tests/ArgumentParserGenerateManualTests/GenerateManualTests.swift` lines 16-16 — location member; effect enclosing struct GenerateManualTests
- `parse-error` `Tests/ArgumentParserPackageManagerTests/HelpTests.swift` lines 25-25 — location declaration header; effect enclosing func getErrorText
- `parse-error` `Tests/ArgumentParserPackageManagerTests/HelpTests.swift` lines 38-38 — location declaration header; effect enclosing func getErrorText
- `parse-error` `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift` lines 194-194 — location declaration header; effect enclosing func expectCustomCompletion
- `parse-error` `Tests/ArgumentParserUnitTests/CompletionScriptTests.swift` lines 224-265 — location member; effect enclosing extension SerializedTests.CompletionScriptTests
- `parse-error` `Tests/ArgumentParserUnitTests/NameSpecificationTests.swift` lines 1-273 — location top level; effect no enclosing declaration
- `parse-error` `Tests/ArgumentParserUnitTests/SplitArgumentTests.swift` lines 25-793 — location top level; effect no enclosing declaration
- `parse-error` `Tests/ArgumentParserUnitTests/UsageGenerationTests.swift` lines 18-247 — location top level; effect no enclosing declaration
