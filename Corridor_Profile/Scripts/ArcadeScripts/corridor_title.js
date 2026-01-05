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
      displayText = feature["Corridor"] + " Corridor Profile"; 
    } else {
      // CASE B: Nothing selected -> Count ALL unique corridors
      var allFeatures = fullSource.layer;
      var uniqueCorridors = Distinct(allFeatures, "Corridor");
      var totalCount = Count(uniqueCorridors);
      
      displayText = "Fort Worth District Corridors with Greatest Needs";
      //displayText = "Fort Worth District has " + Text(totalCount) + " Corridors";
    }
} else {
    displayText = "Error: The widget does not have access to the data.";
}

// 4. RETURN WITH FORMATTING
return {
  value: displayText,
  text: {
    size: 22,          
    bold: true,        
    color: 'rgb(0, 86, 169)',
    italic: false,
    underline: false,
    strike: false
  }
};