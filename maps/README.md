# maps/

- `map.yaml` + `map.pgm`: bản đồ gốc do SLAM Toolbox sinh ra (căn nhà `small_house`, độ phân giải 0,05 m, gốc khung `map` là chỗ robot xuất phát). `free_thresh: 0.196` để Nav2 hiểu pixel 205 là chưa biết.
- `map_clean.yaml` + `map_clean.pgm`: cùng bản đồ, đã làm sạch (điền thân đồ nội thất thành vật cản, giữ vùng chưa biết ngoài tường).
