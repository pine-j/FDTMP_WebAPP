// Documentation: https://arcg.is/18ejKn3

// 1. The ID for the Selection
// NOTE: This ID matches the specific widget configuration in the Experience Builder app.
var selectionID = "dataSource_56-19abd51320a-layer-1-19abd51336a-layer-3-selection";
var selectionSource = $dataSources[selectionID];

// 2. AUTOMATICALLY fix the ID for the Full Layer
// We take the selection ID and remove "-selection" from the end to find the "Default" view ID
var fullLayerID = Replace(selectionID, "-selection", "");

var displayText = "";

function formatCompact(n) {
  if (IsEmpty(n)) return '$0';
  var abs_n = Abs(n);
  
  if (abs_n < 1000) {
    return "$" + Round(n, 1);
  } else if (abs_n < 1000000) {
    return "$" + Round(n / 1000, 1) + "K";
  } else if (abs_n < 1000000000) {
    return "$" + Round(n / 1000000, 1) + "M";
  } else {
    return "$" + Round(n / 1000000000, 1) + "B";
  }
}

// 3. LOGIC
if (HasKey($dataSources, fullLayerID)) {
    var fullSource = $dataSources[fullLayerID];
    var selectedFeatures = selectionSource.selectedFeatures;

    if (Count(selectedFeatures) > 0) {
      // CASE A: Something is selected
      var feature = First(selectedFeatures);
      
      // Try to get Project_Cost_Construction directly first
      var value = feature["Project_Cost_Construction"];
      
      if (IsEmpty(value)) {
        // Fallback: Find this feature in the full source
        // We use Total_Miles as a "fingerprint" to find the matching feature
        var targetMiles = feature["Total_Miles"];
        
        if (!IsEmpty(targetMiles)) {
            var allFeats = fullSource.layer;
            for (var f in allFeats) {
                if (Abs(f["Total_Miles"] - targetMiles) < 0.01) {
                    value = f["Project_Cost_Construction"];
                    break; // Found it
                }
            }
        }
      }

      // Display the Project_Cost_Construction for the selected feature
      if (!IsEmpty(value)) {
         displayText = formatCompact(value);
      } else {
         displayText = "$0";
      }
    } else {
      // CASE B: Nothing selected -> Sum total Project_Cost_Construction
      var allFeatures = fullSource.layer;
      var totalValue = Sum(allFeatures, "Project_Cost_Construction");
      
      displayText = formatCompact(totalValue);
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