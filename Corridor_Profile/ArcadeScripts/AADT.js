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
      // Since AADT might be missing from the selection view, 
      // we will try to find the matching feature in the FULL source.
      
      var selFeature = First(selectedFeatures);
      
      // Try to get AADT directly first
      var valAADT = selFeature["AADT"];
      
      if (IsEmpty(valAADT)) {
        // Fallback: Find this feature in the full source
        // We use Total_Miles as a "fingerprint" to find the matching feature
        // if we don't know the exact unique ID field name.
        var targetMiles = selFeature["Total_Miles"];
        
        if (!IsEmpty(targetMiles)) {
            // Look for feature with same miles in full layer
            // (Assuming mostly unique lengths for corridors)
            var allFeats = fullSource.layer;
            for (var f in allFeats) {
                if (Abs(f["Total_Miles"] - targetMiles) < 0.01) {
                    valAADT = f["AADT"];
                    break; // Found it
                }
            }
        }
      }
      
      if (!IsEmpty(valAADT) && valAADT > 0) {
        displayText = Text(valAADT, "#,###");
      } else {
        displayText = "0";
      }
      
    } else {
      // CASE B: Nothing selected -> Calculate weighted average for all features
      var allFeatures = fullSource.layer;
      var sumWeightedAADT = 0;
      var sumTotalMiles = 0;
      
      for (var feature in allFeatures) {
        var aadt = feature["AADT"];
        var totalMiles = feature["Total_Miles"];
        
        if (!IsEmpty(aadt) && !IsEmpty(totalMiles) && Number(aadt) > 0 && Number(totalMiles) > 0) {
          sumWeightedAADT += (Number(aadt) * Number(totalMiles));
          sumTotalMiles += Number(totalMiles);
        }
      }
      
      // Calculate weighted average
      if (sumTotalMiles > 0) {
        var weightedAvgAADT = sumWeightedAADT / sumTotalMiles;
        displayText = Text(Round(weightedAvgAADT, 0), "#,###");
      } else {
        displayText = "0";
      }
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