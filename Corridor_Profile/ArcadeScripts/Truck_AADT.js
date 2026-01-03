// Documentation: https://arcg.is/18ejKn3

// 1. The ID for the Selection
// NOTE: This ID matches the specific widget configuration in the Experience Builder app.
var selectionID = "dataSource_56-19abd51320a-layer-1-19abd51336a-layer-3-selection";
var selectionSource = $dataSources[selectionID];

// 2. AUTOMATICALLY fix the ID for the Full Layer
var fullLayerID = Replace(selectionID, "-selection", "");

var displayText = "";

// Helper function to safely get values even if field is missing from schema
function GetVal(feat, key) {
    if (HasKey(feat, key)) {
        return feat[key];
    }
    return null;
}

// Helper function: Compact Number Formatting (Arcade Version)
// Replicates logic: <1K raw, <1M K, <1B M, >=1B B
// Logic handles trimming zeros and max 1 decimal place
function FormatCompact(n) {
    if (IsEmpty(n) || IsNan(n)) return "0";

    var val = Number(n);
    var absVal = Abs(val);
    var sign = 1;
    if (val < 0) { sign = -1; }
    
    var suffix = "";
    var num = absVal;
    
    if (absVal >= 1000000000) {
        num = absVal / 1000000000;
        suffix = "B";
    } else if (absVal >= 1000000) {
        num = absVal / 1000000;
        suffix = "M";
    } else if (absVal >= 1000) {
        num = absVal / 1000;
        suffix = "K";
    }
    
    // Apply sign back
    num = num * sign;

    // Round to 1 decimal place
    var rounded = Round(num, 1);
    
    // Text() with "#.################" ensures:
    // 1. No scientific notation
    // 2. No grouping (commas) - matches useGrouping: false
    // 3. Drops trailing zeros and decimal point (e.g. "1.0" becomes "1")
    return Text(rounded, "#.################") + suffix;
}

// 3. LOGIC
if (HasKey($dataSources, fullLayerID)) {
    var fullSource = $dataSources[fullLayerID];
    var selectedFeatures = selectionSource.selectedFeatures;

    var valTruckAADT = 0;
    var valTotalAADT = 0;
    var valTons = 0;
    
    var hasData = false;

    if (Count(selectedFeatures) > 0) {
      // CASE A: Something is selected
      var selFeature = First(selectedFeatures);
      
      valTruckAADT = GetVal(selFeature, "Truck_AADT");
      valTotalAADT = GetVal(selFeature, "AADT");
      valTons = GetVal(selFeature, "Tons");
      
      // Fallback: If Truck_AADT or Tons is missing
      if (IsEmpty(valTruckAADT) || IsEmpty(valTons)) {
        var targetMiles = GetVal(selFeature, "Total_Miles");
        
        if (!IsEmpty(targetMiles)) {
            var allFeats = fullSource.layer;
            for (var f in allFeats) {
                var fMiles = GetVal(f, "Total_Miles");
                if (!IsEmpty(fMiles) && Abs(Number(fMiles) - Number(targetMiles)) < 0.01) {
                    valTruckAADT = GetVal(f, "Truck_AADT");
                    valTotalAADT = GetVal(f, "AADT");
                    valTons = GetVal(f, "Tons");
                    break; 
                }
            }
        }
      }
      
      // Check if we have data now
      if (!IsEmpty(valTruckAADT)) {
          hasData = true;
      }
      
    } else {
      // CASE B: Nothing selected -> Calculate weighted average for all features
      var allFeatures = fullSource.layer;
      
      var sumWeightedTruckAADT = 0;
      var sumWeightedTotalAADT = 0;
      var sumWeightedTons = 0;
      var sumTotalMiles = 0;
      
      for (var feature in allFeatures) {
        var t_aadt = GetVal(feature, "Truck_AADT");
        var aadt = GetVal(feature, "AADT");
        var tons = GetVal(feature, "Tons");
        var totalMiles = GetVal(feature, "Total_Miles");
        
        var n_t_aadt = Number(t_aadt);
        var n_aadt = Number(aadt);
        var n_tons = Number(tons);
        var n_miles = Number(totalMiles);

        if (n_t_aadt > 0 && n_miles > 0) {
          sumWeightedTruckAADT += (n_t_aadt * n_miles);
          sumWeightedTotalAADT += (n_aadt * n_miles);
          sumWeightedTons += (n_tons * n_miles);
          sumTotalMiles += n_miles;
        }
      }
      
      if (sumTotalMiles > 0) {
        valTruckAADT = sumWeightedTruckAADT / sumTotalMiles;
        valTotalAADT = sumWeightedTotalAADT / sumTotalMiles;
        valTons = sumWeightedTons / sumTotalMiles;
        hasData = true;
      }
    }
    
    // Format Output: <Truck_AADT / Truck % / Tons>
    if (hasData) {
        var numTruck = Number(valTruckAADT);
        var numTotal = Number(valTotalAADT);
        var numTons = Number(valTons);

        var textTruckAADT = Text(Round(numTruck, 0), "#,###");
        
        var textPercent = "0%";
        if (numTotal > 0) {
            var pct = numTruck / numTotal;
            textPercent = Text(pct, "#%");
        }
        
        // Apply Compact Formatting to Tons
        var textTons = FormatCompact(numTons);
        
        displayText = textTruckAADT + " / " + textPercent + " / " + textTons + " Tons";
    } else {
        displayText = "0 / 0% / 0";
    }

} else {
    displayText = "Error: Data Source Not Found";
}

// 4. RETURN WITH FORMATTING
return {
  value: displayText,
  text: {
    size: 20,          
    bold: true,        
    color: 'rgb(0, 86, 169)',
    italic: false,
    underline: false,
    strike: false
  }
};
