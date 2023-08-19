#ifndef PLUGIN_MODIFY_H
#define PLUGIN_MODIFY_H

#include "gradual_flow/gcode_path.h"

#include "plugin/broadcast.h"
#include "plugin/metadata.h"
#include "plugin/settings.h"

#include <boost/asio/awaitable.hpp>
#include <spdlog/spdlog.h>

#include <coroutine>
#include <filesystem>
#include <fstream>
#include <memory>

namespace plugin::gradual_flow
{
static int svg_counter = 0;

template<class T, class Rsp, class Req>
struct Generate
{
    using service_t = std::shared_ptr<T>;
    service_t generate_service{ std::make_shared<T>() };
    Broadcast::shared_settings_t settings{ std::make_shared<Broadcast::settings_t>() };
    std::shared_ptr<Metadata> metadata{ std::make_shared<Metadata>() };

    boost::asio::awaitable<void> run()
    {
        while (true)
        {
            grpc::ServerContext server_context;

            cura::plugins::slots::gcode_paths::v0::modify::CallRequest request;
            grpc::ServerAsyncResponseWriter<Rsp> writer{ &server_context };
            co_await agrpc::request(&T::RequestCall, *generate_service, server_context, request, writer, boost::asio::use_awaitable);

            Rsp response;
            auto client_metadata = getUuid(server_context);

            grpc::Status status = grpc::Status::OK;
            try
            {
                auto global_settings = settings.get()->at(client_metadata);

                if (!global_settings.gradual_flow_enabled)
                {
                    // TODO
                }

                std::vector<GCodePath> gcode_paths;
                for (int i = 0; i < request.gcode_paths().size(); ++i)
                {
                    const auto& gcode_path_msg = request.gcode_paths().at(i);

                    geometry::polyline<> points;
                    /*
                     * We need to add the last point of the previous path to the current path
                     * since the paths in Cura are a connected line string and a new path begins
                     * where the previous path ends (see figure below).
                     *    {                Path A            } {          Path B        } {   ....
                     *    a.1-----------a.2------a.3---------a.4------b.1--------b.2--- c.1---....
                     * For our purposes it is easier that each path is a separate line string, and
                     * no knowledge of the previous path is needed.
                     */
                    if (i >= 1)
                    {
                        const auto& prev_path = &request.gcode_paths().at(i - 1).path().path();
                        if (!prev_path->empty())
                        {
                            const auto& point = prev_path->at(prev_path->size() - 1); // prev_path->end();
                            points.push_back(ClipperLib::IntPoint(point.x(), point.y()));
                        }
                    }

                    for (const auto& point : gcode_path_msg.path().path())
                    {
                        points.push_back(ClipperLib::IntPoint(point.x(), point.y()));
                    }

                    auto gcode_path = GCodePath
                    {
                        .original_gcode_path_data = &gcode_path_msg,
                        .points = points,
                    };

                    gcode_paths.push_back(gcode_path);
                }

                GCodeState state
                {
                    .current_flow = 0., // initial flow is 0
                    .flow_acceleration = request.layer_nr() == 0 ? global_settings.layer_0_max_flow_acceleration : global_settings.max_flow_acceleration,
                    .discretized_duration = global_settings.gradual_flow_discretisation_step_size,
                };

                const auto limited_flow_acceleration_paths = state.processGcodePaths(gcode_paths);

                for (const auto& gcode_path : limited_flow_acceleration_paths)
                {
                    auto gcode_path_message = gcode_path.to_grpc_message();
                    response.add_gcode_paths()->CopyFrom(gcode_path_message);
                }

                // save svg of the original gcode paths
                {
                    std::string svg = "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 200 200\">\n";
                    for (auto &gcode_path: gcode_paths) {
                        svg += gcode_path.toSvgPath() + "\n";
                    }
                    svg += "</svg>";

                    auto svg_path = fmt::format("svg/svg_{}_original.svg", svg_counter ++);
                    spdlog::info("svg_path: {}", svg_path);

                    std::ofstream svg_file;
                    svg_file.open(svg_path);
                    svg_file << svg;
                    svg_file.close();
                };

                // save svg of the discretized gcode paths
                {
                    std::string svg = "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 200 200\">\n";
                    for (auto &gcode_path: limited_flow_acceleration_paths) {
                        svg += gcode_path.toSvgPath() + "\n";
                    }
                    svg += "</svg>";

                    auto svg_path = fmt::format("svg/svg_{}_discretized_path.svg", svg_counter ++);
                    spdlog::info("svg_path: {}", svg_path);

                    std::ofstream svg_file;
                    svg_file.open(svg_path);
                    svg_file << svg;
                    svg_file.close();
                };
            }
            catch (const std::exception& e)
            {
                spdlog::error("Error: {}", e.what());
                status = grpc::Status(grpc::StatusCode::INTERNAL, static_cast<std::string>(e.what()));
            }

            if (! status.ok())
            {
                co_await agrpc::finish_with_error(writer, status, boost::asio::use_awaitable);
                continue;
            }
            co_await agrpc::finish(writer, response, status, boost::asio::use_awaitable);
        }
    }
};

} // namespace plugin

#endif // PLUGIN_MODIFY_H
