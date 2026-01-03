// Documentation: https://arcg.is/18ejKn3

// 1. The ID for the Selection
// NOTE: This ID matches the specific widget configuration in the Experience Builder app.
var selectionID = "dataSource_56-19abd51320a-layer-1-19abd51336a-layer-3-selection";
var selectionSource = $dataSources[selectionID];

// 2. AUTOMATICALLY fix the ID for the Full Layer
// We take the selection ID and remove "-selection" from the end to find the "Default" view ID
var fullLayerID = Replace(selectionID, "-selection", "");

var displayText = "";
var DEBUG = true; // Set to false after verifying HWY matching

function Log(msg) {
    if (DEBUG) {
        Console(msg);
    }
}

// Helper function to safely get values even if field is missing from schema
function GetVal(feat, key) {
    if (HasKey(feat, key)) {
        return feat[key];
    }
    return null;
}

function NormalizeKey(value) {
    if (IsEmpty(value)) {
        return null;
    }
    return Lower(Trim(Text(value)));
}

// 3. LOGIC
if (HasKey($dataSources, fullLayerID)) {
    var fullSource = $dataSources[fullLayerID];
    var selectedFeatures = selectionSource.selectedFeatures;

    if (Count(selectedFeatures) > 0) {
      // CASE A: Something is selected
      var miles4Dplus = 0;
      var allFeats = fullSource.layer;
      
      // Loop through each selected feature
      for (var selFeature in selectedFeatures) {
          // 1. Try to get value directly
          var val = GetVal(selFeature, "four_D_plus_miles");
          
          // 2. Fallback logic if direct value is missing
          if (IsEmpty(val)) {
              var foundMatch = false;
              
              // STRATEGY A: Match by HWY (Best, Unique)
              var targetHWY = GetVal(selFeature, "HWY");
              if (!IsEmpty(targetHWY)) {
                  var targetKey = Lower(Trim(Text(targetHWY)));
                  
                  for (var f in allFeats) {
                      var fHWY = GetVal(f, "HWY");
                      if (!IsEmpty(fHWY)) {
                          if (Lower(Trim(Text(fHWY))) == targetKey) {
                              val = GetVal(f, "four_D_plus_miles");
                              foundMatch = true;
                              break; 
                          }
                      }
                  }
              }
              
              // STRATEGY B: Match by Total_Miles (Backup if HWY missing/failed)
              if (!foundMatch) {
                   var targetMiles = GetVal(selFeature, "Total_Miles");
                   if (!IsEmpty(targetMiles)) {
                      for (var f in allFeats) {
                          var fMiles = GetVal(f, "Total_Miles");
                          if (!IsEmpty(fMiles) && Abs(Number(fMiles) - Number(targetMiles)) < 0.01) {
                              val = GetVal(f, "four_D_plus_miles");
                              foundMatch = true;
                              break; 
                          }
                      }
                   }
              }
          }
          
          // Add to total if we found a value
          if (!IsEmpty(val)) {
              miles4Dplus += Number(val);
          }
      }
      
      displayText = Text(miles4Dplus, "#,###.0") + " mi";
    } else {
      // CASE B: Nothing selected -> Sum total 4D+ miles
      var allFeatures = fullSource.layer;
      var total4DplusMiles = Sum(allFeatures, "four_D_plus_miles");
      
      displayText = Text(total4DplusMiles, "#,###.0") + " mi";
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