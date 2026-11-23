// 16-bit population counter with two clocked pipeline stages.
module popcount16 (
    input wire clk,
    input wire [15:0] bits,
    output reg [4:0] count
);
    reg [15:0] bits_reg;
    reg [4:0] count_comb;
    integer i;
    always @* begin
        count_comb = 5'd0;
        for (i = 0; i < 16; i = i + 1)
            count_comb = count_comb + {4'd0, bits_reg[i]};
    end
    always @(posedge clk) begin
        bits_reg <= bits;
        count <= count_comb;
    end
endmodule
