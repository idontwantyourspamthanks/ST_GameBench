require "json"
out = {}
ARGV.each do |f|
  r = Hub::Ncmp::Parser.parse(File.binread(f))
  out[File.basename(f)] = { "levels" => r.levels.map { |l| { "mission" => l.mission, "tower" => l.tower, "rows" => l.rows, "time_bcd" => l.time_bcd, "name" => l.name, "colours" => l.colours, "enemy_set" => l.enemy_set, "grid" => l.grid, "record" => l.record.unpack1("H*") } },
                            "playlists" => r.playlists.map { |p| { "name" => p[:name], "entries" => p[:entries] } } }
end
puts JSON.generate(out)
