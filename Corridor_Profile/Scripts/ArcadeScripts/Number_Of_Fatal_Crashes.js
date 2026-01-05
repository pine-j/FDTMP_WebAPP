// Documentation: https://arcg.is/18ejKn3

// 1. The ID for the Selection
// NOTE: This ID matches the specific widget configuration in the Experience Builder app.
var selectionID = "dataSource_56-19abd51320a-layer-1-19abd51336a-layer-3-selection";
var selectionSource = $dataSources[selectionID];

// 2. AUTOMATICALLY fix the ID for the Full Layer
// We take the selection ID and remove "-selection" from the end to find the "Default" view ID
var fullLayerID = Replace(selectionID, "-selection", "");

var displayText = "";

// 3. LOGIC
if (HasKey($dataSources, fullLayerID)) {
    var fullSource = $dataSources[fullLayerID];
    var selectedFeatures = selectionSource.selectedFeatures;

    if (Count(selectedFeatures) > 0) {
      // CASE A: Something is selected
      var feature = First(selectedFeatures);
      
      // Try to get Number_Of_Fatal_Crashes directly first
      var fatalCrashes = feature["Number_Of_Fatal_Crashes"];
      
      if (IsEmpty(fatalCrashes)) {
        // Fallback: Find this feature in the full source
        // We use Total_Miles as a "fingerprint" to find the matching feature
        var targetMiles = feature["Total_Miles"];
        
        if (!IsEmpty(targetMiles)) {
            var allFeats = fullSource.layer;
            for (var f in allFeats) {
                if (Abs(f["Total_Miles"] - targetMiles) < 0.01) {
                    fatalCrashes = f["Number_Of_Fatal_Crashes"];
                    break; // Found it
                }
            }
        }
      }

      // Display the Number_Of_Fatal_Crashes for the selected feature
      if (!IsEmpty(fatalCrashes)) {
         displayText = Text(fatalCrashes, "#,###");
      } else {
         displayText = "0";
      }
    } else {
      // CASE B: Nothing selected -> Sum total fatal crashes
      var allFeatures = fullSource.layer;
      var totalFatalCrashes = Sum(allFeatures, "Number_Of_Fatal_Crashes");
      
      displayText = Text(totalFatalCrashes, "#,###");
    }
} else {
    displayText = "Error: The widget does not have access to the data.";
}

// 4. RETURN WITH FORMATTING
return {
  value: displayText,
  text: {
    size: 20,          // 20px
    bold: true,        // Bold
    color: 'rgb(0, 86, 169)',
    italic: false,
    underline: false,
    strike: false
  }
};

